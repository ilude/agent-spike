#!/usr/bin/env python
"""Cluster video embeddings into personas using k-means.

Tests different k values and outputs cluster assignments with quality metrics.
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

OUTPUT_DIR = Path(__file__).parent / "output"

# K values to test
K_VALUES = [5, 6, 7, 8, 10]


def load_embeddings() -> tuple[list[dict], np.ndarray]:
    """Load video embeddings from file.

    Returns:
        Tuple of (video metadata list, embedding matrix)
    """
    embeddings_file = OUTPUT_DIR / "video_embeddings.json"
    if not embeddings_file.exists():
        raise FileNotFoundError(
            "No video_embeddings.json found. Run generate_embeddings.py first."
        )

    with open(embeddings_file) as f:
        data = json.load(f)

    videos = data["videos"]
    embeddings = np.array([v["embedding"] for v in videos])

    return videos, embeddings


def cluster_and_evaluate(embeddings: np.ndarray, k: int) -> tuple[KMeans, float]:
    """Run k-means clustering and compute silhouette score.

    Args:
        embeddings: NxD matrix of embeddings
        k: Number of clusters

    Returns:
        Tuple of (fitted KMeans model, silhouette score)
    """
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)
    score = silhouette_score(embeddings, labels)
    return kmeans, score


def get_cluster_samples(
    videos: list[dict],
    labels: np.ndarray,
    k: int,
    samples_per_cluster: int = 5,
) -> dict[int, list[dict]]:
    """Get sample videos from each cluster.

    Args:
        videos: List of video metadata
        labels: Cluster assignments
        k: Number of clusters
        samples_per_cluster: How many samples to take per cluster

    Returns:
        Dict mapping cluster index to list of sample videos
    """
    samples = {}
    for cluster_idx in range(k):
        cluster_videos = [
            videos[i] for i, label in enumerate(labels) if label == cluster_idx
        ]
        # Take first N samples
        samples[cluster_idx] = cluster_videos[:samples_per_cluster]
    return samples


def main():
    """Cluster video embeddings and evaluate different k values."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load embeddings
    try:
        videos, embeddings = load_embeddings()
    except FileNotFoundError as e:
        print(e)
        return

    print(f"Loaded {len(videos)} videos with {embeddings.shape[1]}-dim embeddings")

    # Test different k values
    results = []
    print("\nTesting k values:")
    print("-" * 40)

    for k in K_VALUES:
        if k > len(videos):
            print(f"k={k}: Skipped (more clusters than videos)")
            continue

        kmeans, score = cluster_and_evaluate(embeddings, k)

        # Count cluster sizes
        labels = kmeans.labels_
        cluster_sizes = [int(np.sum(labels == i)) for i in range(k)]

        print(f"k={k}: silhouette={score:.3f}, sizes={cluster_sizes}")

        results.append({
            "k": k,
            "silhouette_score": score,
            "cluster_sizes": cluster_sizes,
            "inertia": kmeans.inertia_,
        })

    # Find best k by silhouette score
    best_result = max(results, key=lambda x: x["silhouette_score"])
    best_k = best_result["k"]
    print(f"\nBest k={best_k} (silhouette={best_result['silhouette_score']:.3f})")

    # Re-run clustering with best k to save results
    kmeans, _ = cluster_and_evaluate(embeddings, best_k)
    labels = kmeans.labels_

    # Get samples from each cluster
    samples = get_cluster_samples(videos, labels, best_k, samples_per_cluster=10)

    # Build output
    clusters = []
    for cluster_idx in range(best_k):
        cluster_video_ids = [
            videos[i]["video_id"] for i, label in enumerate(labels) if label == cluster_idx
        ]
        cluster_titles = [
            videos[i]["title"] for i, label in enumerate(labels) if label == cluster_idx
        ]

        clusters.append({
            "index": cluster_idx,
            "label": None,  # To be filled in manually
            "size": len(cluster_video_ids),
            "video_ids": cluster_video_ids,
            "sample_titles": cluster_titles[:10],
            "centroid": kmeans.cluster_centers_[cluster_idx].tolist(),
        })

    # Save results
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "k": best_k,
        "silhouette_score": best_result["silhouette_score"],
        "total_videos": len(videos),
        "k_evaluation": results,
        "clusters": clusters,
    }

    output_file = OUTPUT_DIR / "persona_clusters.json"
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved to: {output_file}")

    # Also save cluster assignments for each video
    assignments = []
    for i, video in enumerate(videos):
        assignments.append({
            "video_id": video["video_id"],
            "title": video["title"],
            "cluster": int(labels[i]),
        })

    assignments_file = OUTPUT_DIR / "cluster_assignments.json"
    with open(assignments_file, "w") as f:
        json.dump({
            "k": best_k,
            "assignments": assignments,
        }, f, indent=2)

    print(f"Assignments saved to: {assignments_file}")

    # Print cluster summary
    print("\n" + "=" * 60)
    print("CLUSTER SUMMARY")
    print("=" * 60)

    for cluster in clusters:
        print(f"\nCluster {cluster['index']} ({cluster['size']} videos):")
        print("-" * 40)
        for title in cluster["sample_titles"][:5]:
            # Clean up title
            clean_title = title.replace("Watched ", "")[:60]
            print(f"  - {clean_title}")


if __name__ == "__main__":
    main()
