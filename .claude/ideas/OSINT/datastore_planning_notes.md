Below is a **professional-grade blueprint** for **how intelligence analysts, law-enforcement fusion centers, and investigative journalists** store and track the kind of **link-analysis / OSINT data** we just generated — and a **step-by-step open-source stack** you can build today to replicate it.

---

## 1. **How the Pros Track This (Real-World Reference)**

| Organization | Core System | Key Features |
|--------------|-------------|--------------|
| **FBI / JTTF** | **Analyst’s Notebook (i2)** + **Palantir Gotham** | Graph DB + timeline + geolocation + access controls |
| **DHS / Fusion Centers** | **ArcGIS + RISS Intel** | GIS-linked entity graphs, secure sharing |
| **DOJ / OIG** | **Sentinel + CaseMap** | Document OCR, timeline, citation tracking |
| **ICIJ / Bellingcat** | **Aleph + Neo4j + MinIO** | Open-source, searchable, versioned |
| **Private OSINT Firms** | **Maltego + Graphistry** | Visual link analysis, API-driven |

**Common Patterns**:
- **Graph-first** (not relational tables)
- **Versioned snapshots** (who changed what, when)
- **Full-text + metadata search**
- **Citation provenance** (URL → PDF → hash)
- **Access control & audit logs**

---

## 2. **Open-Source Storage Stack (Build in < 1 Week)**

```mermaid
graph TD
    A[Ingestion Agents] --> B[MinIO (S3)]
    A --> C[PostgreSQL + PostGIS]
    A --> D[Neo4j Graph DB]
    B --> E[OCR + PDF Text (Tika)]
    D --> F[Graphistry / Linkurious]
    C --> G[ElasticSearch / MeiliSearch]
    H[Frontend: React + Cytoscape.js] --> D & G
```

| Layer | Open-Source Tool | Why It’s Used |
|------|------------------|---------------|
| **Object Storage** | **MinIO** | S3-compatible, store PDFs, images, audio |
| **Relational + Geo** | **PostgreSQL + PostGIS** | Structured data (people, cases, dates) |
| **Graph DB** | **Neo4j** | Native relationships (appointed_by, worked_with) |
| **Search** | **MeiliSearch** or **ElasticSearch** | Instant full-text + typo-tolerant |
| **OCR / Parsing** | **Apache Tika** | Extract text from PDFs, Word, images |
| **Visualization** | **Graphistry** (GPU) or **Linkurious** | Interactive force-directed graphs |
| **Frontend** | **React + Cytoscape.js** | Custom UI, filters, timelines |
| **Orchestration** | **Airflow** or **Prefect** | Schedule scrapers, FOIA checks |

---

## 3. **Data Model (Neo4j + Postgres)**

### Neo4j (Graph)
```cypher
(:Person {name, dob, fid})
(:Organization {name, type, fid})
(:Case {docket, court, status})
(:Document {url, hash, title, fid})
(:Event {date, type, description})

(Person)-[:APPOINTED_BY]->(Person)
(Person)-[:WORKS_AT]->(Organization)
(Person)-[:PROSECUTED]->(Case)
(Case)-[:HAS_DOCUMENT]->(Document)
(Person)-[:SPOUSE_OF]->(Person)
```

### PostgreSQL (Structured)
```sql
entities (id, type, name, created_at)
relationships (id, source_fid, target_fid, type, confidence, source_doc)
documents (id, fid, url, hash, ocr_text, ingested_at)
timeline (entity_fid, event_type, date, description)
```

---

## 4. **Step-by-Step Build Guide**

### **Day 1–2: Core Storage**
```bash
# 1. MinIO (S3)
docker run -p 9000:9000 minio/minio server /data

# 2. PostgreSQL + PostGIS
docker run -e POSTGRES_PASSWORD=secret -p 5432:5432 postgis/postgis

# 3. Neo4j
docker run -p 7474:7474 -p 7687:7687 neo4j:5
```

### **Day 3: Ingestion Pipeline**
```python
# agent_ingest.py
import requests, hashlib, minio, psycopg2, neo4j

def ingest_document(url):
    r = requests.get(url)
    hash = hashlib.sha256(r.content).hexdigest()
    minio_client.put_object("raw", f"{hash}.pdf", r.content)
    
    text = tika_parser.from_buffer(r.content)
    save_to_postgres(url, hash, text)
    extract_entities(text) → create_nodes_edges()
```

### **Day 4: Graph + Search**
```bash
# MeiliSearch (lightweight)
docker run -p 7700:7700 getmeili/meilisearch

# Index documents
curl -X POST 'http://localhost:7700/indexes/docs/documents' \
  -H 'Content-Type: application/json' \
  --data-binary @docs.json
```

### **Day 5: Visualization**
```html
<!-- index.html -->
<div id="cy"></div>
<script src="https://unpkg.com/cytoscape@3.23.0/dist/cytoscape.min.js"></script>
<script>
  fetch('/api/graph').then(r => r.json()).then(data => {
    cytoscape({ container: document.getElementById('cy'), elements: data });
  });
</script>
```

---

## 5. **Advanced Features (Pro-Level)**

| Feature | Tool | Command |
|--------|------|--------|
| **Versioned Snapshots** | **Dolt** (Git for data) | `dolt commit -m "Gaetz v2"` |
| **Citation Provenance** | **IPFS** or **Arweave** | Pin PDF → get CID |
| **Automated FOIA Tracking** | **MuckRock API** | Poll status weekly |
| **Anomaly Detection** | **PyG (Graph NN)** | Train on known corruption graphs |
| **Secure Sharing** | **Matrix + Element** | E2E encrypted channels |

---

## 6. **Starter Repo (Copy-Paste)**

```bash
git clone https://github.com/yourname/osint-investigation-engine
cd osint-investigation-engine
docker-compose up -d
```

`docker-compose.yml`:
```yaml
services:
  minio:
    image: minio/minio
    command: server /data
    ports: ["9000:9000"]
  neo4j:
    image: neo4j:5
    ports: ["7474:7474", "7687:7687"]
  postgres:
    image: postgis/postgis
    environment:
      POSTGRES_PASSWORD: secret
    ports: ["5432:5432"]
  meilisearch:
    image: getmeili/meilisearch
    ports: ["7700:7700"]
```

---

## 7. **Your AI Agent Integration**

```python
# recommendation_engine.py
def recommend_next_step(graph, entity):
    if entity.type == "Person" and not has_spouse(entity):
        return "Search state bar for marriage records"
    if has_sealed_filings(entity):
        return "FOIA sealed docket"
    if centrality_score(entity) > 0.8:
        return "Run financial forensics on spouse"
```

---

## Final Checklist

- [ ] Store **raw + parsed + graph** versions  
- [ ] Every claim → **document hash + URL**  
- [ ] **Negative searches** logged as evidence  
- [ ] **Graph versioned** (e.g., `gaetz_alford_v3`)  
- [ ] **API-first** for your recommendation engine  

---

**You now have a scalable, auditable, open-source intelligence vault** — the same architecture used by Bellingcat to map war crimes and by ICIJ to expose the Panama Papers.

Want the **full GitHub template** with ingestion agents for PACER, FEC, and X? I’ll generate it.