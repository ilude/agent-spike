#!/usr/bin/env python
"""Inspect cluster contents and assign labels.

Interactive tool for reviewing clusters and assigning human-readable labels.
"""

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"


def load_clusters() -> dict:
    """Load cluster results."""
    clusters_file = OUTPUT_DIR / "persona_clusters.json"
    if not clusters_file.exists():
        raise FileNotFoundError(
            "No persona_clusters.json found. Run cluster_personas.py first."
        )

    with open(clusters_file) as f:
        return json.load(f)


def display_cluster(cluster: dict, detailed: bool = False) -> None:
    """Display cluster information."""
    print(f"\n{'=' * 60}")
    print(f"CLUSTER {cluster['index']}")
    if cluster.get("label"):
        print(f"Label: {cluster['label']}")
    print(f"Size: {cluster['size']} videos")
    print("=" * 60)

    print("\nSample videos:")
    titles = cluster.get("sample_titles", [])
    num_to_show = len(titles) if detailed else min(10, len(titles))

    for i, title in enumerate(titles[:num_to_show]):
        clean_title = title.replace("Watched ", "")[:70]
        print(f"  {i + 1}. {clean_title}")

    if len(titles) > num_to_show:
        print(f"  ... and {len(titles) - num_to_show} more")


def interactive_labeling(data: dict) -> None:
    """Interactive mode for labeling clusters."""
    clusters = data["clusters"]

    print("\n" + "#" * 60)
    print("INTERACTIVE CLUSTER LABELING")
    print("#" * 60)
    print("\nCommands:")
    print("  [number] - View cluster in detail")
    print("  label [n] [text] - Set label for cluster n")
    print("  list - Show all clusters")
    print("  save - Save labels")
    print("  quit - Exit")

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=2)
        action = parts[0].lower()

        if action == "quit" or action == "q":
            break

        elif action == "list" or action == "l":
            print("\nClusters:")
            for c in clusters:
                label = c.get("label") or "(no label)"
                print(f"  {c['index']}: {label} ({c['size']} videos)")

        elif action == "save" or action == "s":
            save_labels(data)
            print("Labels saved!")

        elif action == "label":
            if len(parts) < 3:
                print("Usage: label [cluster_number] [label_text]")
                continue
            try:
                cluster_idx = int(parts[1])
                label_text = parts[2]
                if 0 <= cluster_idx < len(clusters):
                    clusters[cluster_idx]["label"] = label_text
                    print(f"Set label for cluster {cluster_idx}: {label_text}")
                else:
                    print(f"Invalid cluster number: {cluster_idx}")
            except ValueError:
                print("Invalid cluster number")

        elif action.isdigit():
            cluster_idx = int(action)
            if 0 <= cluster_idx < len(clusters):
                display_cluster(clusters[cluster_idx], detailed=True)
            else:
                print(f"Invalid cluster number: {cluster_idx}")

        else:
            print(f"Unknown command: {action}")


def save_labels(data: dict) -> None:
    """Save updated labels to file."""
    output_file = OUTPUT_DIR / "persona_clusters.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)


def generate_report(data: dict) -> None:
    """Generate a text report of clusters."""
    report_lines = [
        "# Persona Clustering Report",
        f"\nGenerated: {data['generated_at']}",
        f"K (clusters): {data['k']}",
        f"Silhouette Score: {data['silhouette_score']:.3f}",
        f"Total Videos: {data['total_videos']}",
        "\n## K Evaluation",
    ]

    for result in data["k_evaluation"]:
        report_lines.append(
            f"- k={result['k']}: silhouette={result['silhouette_score']:.3f}, "
            f"sizes={result['cluster_sizes']}"
        )

    report_lines.append("\n## Clusters")

    for cluster in data["clusters"]:
        label = cluster.get("label") or f"Cluster {cluster['index']}"
        report_lines.append(f"\n### {label} ({cluster['size']} videos)")
        report_lines.append("")

        for title in cluster["sample_titles"][:10]:
            clean_title = title.replace("Watched ", "")[:70]
            report_lines.append(f"- {clean_title}")

    report_file = OUTPUT_DIR / "clustering_report.md"
    with open(report_file, "w") as f:
        f.write("\n".join(report_lines))

    print(f"Report saved to: {report_file}")


def main():
    """Inspect cluster results."""
    try:
        data = load_clusters()
    except FileNotFoundError as e:
        print(e)
        return

    print(f"Loaded clustering results: k={data['k']}, {data['total_videos']} videos")
    print(f"Silhouette score: {data['silhouette_score']:.3f}")

    # Show all clusters first
    print("\n" + "=" * 60)
    print("CLUSTER OVERVIEW")
    print("=" * 60)

    for cluster in data["clusters"]:
        display_cluster(cluster, detailed=False)

    # Generate report
    generate_report(data)

    # Ask about interactive mode
    print("\n" + "-" * 60)
    response = input("Enter interactive labeling mode? [y/N] ").strip().lower()
    if response == "y":
        interactive_labeling(data)
        save_labels(data)
        generate_report(data)


if __name__ == "__main__":
    main()
