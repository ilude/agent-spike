# How To Be A Scary OSINT Analyst - Complete Methodology

## The Problem
OSINT investigations often fail because analysts rely on guesswork, skip verification steps, or don't know how to systematically extract and connect digital breadcrumbs from minimal starting information. Most guides teach individual tools but not the complete investigation workflow that turns a single photo into a comprehensive target profile.

## The Solution
A 5-phase OSINT investigation methodology demonstrated through a fictional case study of "Alex Kiernan" - starting with only a name, low-quality photo, and unverified location claim, then building a complete corporate and digital profile through systematic enumeration, cross-referencing, and metadata exploitation.

## Why It Works
The methodology works because:
- **Treats all initial information as unverified** - Starts with the most reliable artifact (photo) rather than assumptions
- **Automates breadcrumb discovery** - Uses tools to cast wide nets before manual deep-dives
- **Exploits metadata and OPSEC failures** - Finds information leaks in commit histories, PDF properties, DNS records
- **Chains evidence** - Each discovery opens new investigative paths, building a web of corroborating sources
- **Reports with confidence levels** - Separates verified facts from inferences

## The 5-Phase Methodology

### Phase 1: Target Definition & Reconnaissance

**Goal**: Precisely define target and gather all known starting points

**Starting Information (Example)**:
- Name: "Alex Kiernan" (treat as potentially an alias)
- Low-quality photo from conference
- Potential location: "Miami, Florida" (unverified third-party claim)

**Critical Decision**:
- Name is unverified → treat as unreliable
- Photo is most reliable artifact → use as primary "seed"

### Phase 2: Automated Enumeration & Breadcrumb Collection

**Goal**: Cast wide net using seed to find new leads

#### Action 1: Reverse Image Search

**Tools**:
- Yandex Images (often best for finding obscure matches)
- Google Images
- Bing Visual Search

**Process**: Upload low-quality conference photo

**Example Results**:
- Google Images: Nothing found
- **Yandex Images**: Found cropped version on blog.ru (Russian blogging platform)
  - Post mentions "Конференция по кибербезопасности" (Cybersecurity conference) in **Warsaw**
  - **Contradicts initial "Miami" claim** ✓

**New Lead**: Warsaw Cybersecurity Conference

#### Action 2: Username Enumeration

**Tools**:
- **Sherlock** (username search across platforms)
- **Maigret** (advanced alternative)
- Optional: Advanced search operators

**Command Example**:
```bash
maigret AlexKiernan
```

**Example Findings**:
- **GitHub**: `alexkiernan` - minimal activity, forks privacy-focused tools
- **Twitter/X**: `@ak_cybersec` - 3 tweets about technical vulnerabilities
- **Keybase.io**: `akiernan` - same profile pic as GitHub (different from seed photo)

**New Leads**: Three usernames (`alexkiernan`, `ak_cybersec`, `akiernan`) + three platform accounts

### Phase 3: Deep-Dive Source Analysis

**Goal**: Manually investigate each lead to extract rich information and connections

#### Lead 1: The blog.ru Post

**Action**: Translate Russian content

**Deep Dive Process**:
1. Post is Warsaw conference summary
2. Author tags other attendees
3. Tagged user: `@marcin_nowak` on defunct Polish social network
4. Search: "Marcin Nowak Warsaw Cybersecurity"
5. Find **LinkedIn profile**: Marcin Nowak, Security Researcher at "CryptoShield Labs"
6. Public profile shows connection to **"Kiernan Analytics"**

**Gold Strike**: Company name "Kiernan Analytics" directly linked to POI's surname

#### Lead 2: The GitHub Account `alexkiernan`

**Investigation Areas**:
- Bio
- Commit history
- Starred repositories
- Pinned repositories

**Findings**:
- **Bio**: "Privacy and OSINT enthusiast. DM for Signal" (counter-OSINT mindset)
- **Pinned Repo**: "EXIFScrubber" (operational security focus)
- **Email in Commits**: Check old commits before GitHub-private email configured
  - Found: `akiernan2014@protonmail.com` (from commit 3 years ago)
  - "2014" may indicate account creation year or personal identifier

**Gold Strike**: Personal ProtonMail email address leaked via commit history

**OPSEC Lesson**: Old commits often contain personal emails before privacy measures implemented

#### Lead 3: The Keybase.io Account `akiernan`

**Why Keybase**: Platform designed for proving identity across services via cryptographic proofs

**Investigation**: Check "Proofs" section

**Connected Accounts**:
- Twitter: `@ak_cybersec` (already known)
- GitHub: `alexkiernan` (already known)
- **Domain ownership**: `kiernan-analytics.com` (cryptographically verified)

**Gold Strike**: Confirmed company domain with cryptographic proof of ownership

#### Lead 4: The Company Domain `kiernan-analytics.com`

**Investigation Techniques**:

**1. WHOIS Lookup**:
```
whois kiernan-analytics.com
```
Result: Private registration (dead end)

**2. SecurityTrails - Historical DNS Records**:
- Check historical IP addresses
- Finding: IP from 2 years ago in different hosting block
- Tied to small VPS provider in **Amsterdam**

**New Lead**: Historical server location (Amsterdam)

**3. Website Content Analysis**:
- Minimalist landing page
- Contact form + client login
- No names or locations visible

**4. Source Code Investigation**:
- Inspect HTML source
- Found CSS path: `/wp-content/themes/divi/style.css`
- **Reveals**: Site built on **WordPress** using **Divi theme**
- Can now search for known vulnerabilities in this setup

**5. Google Dorking**:
```
site:kiernan-analytics.com filetype:pdf
```

**Finding**: Hidden, unlinked PDF
```
kiernan-analytics.com/media/whitepaper_q1_2023.pdf
```

**Gold Strike**: The Whitepaper PDF

**6. PDF Metadata Analysis**:

**How to check**:
1. Download PDF
2. Open in PDF reader
3. Check Properties → Author field
4. Check Advanced → Metadata

**Findings**:
- **Author meta-field**: "A. Kiernan"
- **Producer field**: "Skia/PDF m108 Google Docs Viewer"
- **Conclusion**: PDF authored in **Google Docs** before export

**OPSEC Lesson**: Document metadata reveals authorship and creation tools

### Phase 4: Data Fusion & Pattern Analysis

**Goal**: Connect dots to build coherent profile

**Create Link Chart**:

**Core Identity Chain**:
```
Photo → Warsaw Conference → blog.ru post →
Marcin Nowak (LinkedIn) → Kiernan Analytics
```

**Digital Presence**:
```
Name "Alex Kiernan" → Usernames (alexkiernan, akiernan) →
GitHub + Keybase platforms
```

**Corporate Footprint**:
```
Keybase cryptographic proof → kiernan-analytics.com domain ownership
```

**Personal Artifacts**:
```
GitHub commit history → akiernan2014@protonmail.com (email leak)
PDF metadata → Google Docs usage by "A. Kiernan"
```

**Geographic Intelligence**:
- Initial claim: Miami, Florida (contradicted)
- Conference attendance: Warsaw, Poland (verified)
- Historical infrastructure: Amsterdam, Netherlands (VPS hosting)

**The Narrative**:
"Alex Kiernan" is likely a **real name**, not an alias. Privacy-conscious cybersecurity professional running boutique firm "Kiernan Analytics". Operational security is **good but not perfect** - made mistakes in old GitHub commit and PDF metadata. Geographic story complex: professional activity in Warsaw, past server presence in Amsterdam. Not a random actor but technically capable individual.

### Phase 5: Reporting & Verification

**Goal**: Present undeniable findings with confidence levels

**Report Structure**:

#### Subject
Digital Profile Assessment for POI "Alex Kiernan"

#### Verified Facts (High Confidence)

**Finding 1**: POI operates company "Kiernan Analytics" (kiernan-analytics.com)
- **Sources**:
  - Keybase cryptographic proof
  - LinkedIn connection from Marcin Nowak

**Finding 2**: POI uses email `akiernan2014@protonmail.com`
- **Source**: GitHub commit history

**Finding 3**: POI attended "Warsaw Cybersecurity Conference 2023"
- **Source**: Yandex reverse image search correlating POI's photo to blog.ru post

#### Inferred Information (Medium Confidence)

**Inference 1**: POI has technical background in privacy and OSINT with demonstrated coding ability
- **Source**: GitHub repository content and stars

**Inference 2**: POI's company infrastructure previously hosted in Amsterdam
- **Source**: SecurityTrails historical DNS records

#### Open Questions / Required Next Steps

1. **Determine current country of residence**
   - Action: Search business registries for "Kiernan Analytics" in Poland, Netherlands, and UK

2. **Investigate Marcin Nowak's relationship with POI**
   - Action: Find potential associates through network analysis

3. **Check for data breaches**
   - Action: Search `akiernan2014@protonmail.com` in Have I Been Pwned
   - Goal: Find potential password reuse or linked accounts

## Key OSINT Tools & Techniques

### Reverse Image Search
- **Yandex Images** - Often best for obscure/international content
- **Google Images** - Good for mainstream content
- **Bing Visual Search** - Alternative option

**Pro Tip**: Try multiple engines - different results

### Username Enumeration
- **Sherlock** - Python tool for username search across 300+ sites
  ```bash
  sherlock username
  ```
- **Maigret** - Enhanced alternative with more features
  ```bash
  maigret username
  ```

### Domain Intelligence
- **WHOIS lookups** - Domain registration info
- **SecurityTrails** - Historical DNS records, IP changes
- **Archive.org Wayback Machine** - Historical website content

### Google Dorking
Essential operators:
- `site:domain.com` - Search specific domain
- `filetype:pdf` - Find specific file types
- `inurl:` - Search in URLs
- `intitle:` - Search page titles

**Example searches**:
```
site:targetdomain.com filetype:pdf
site:targetdomain.com inurl:admin
site:targetdomain.com intitle:"index of"
```

### Metadata Analysis
**PDF Metadata**:
- Author field
- Creation date
- Producer/Creator software
- Modification history

**Image EXIF Data**:
- GPS coordinates
- Camera model
- Software used
- Creation timestamp

**Tools**:
- ExifTool (command line)
- PDF readers (Properties → Advanced → Metadata)

### Platform-Specific Techniques

**GitHub**:
- Check commit history for email leaks
- Review starred repositories (interests)
- Check forked projects
- Look at issue/PR comments

**LinkedIn**:
- Public connections
- Shared group memberships
- Job history timeline
- Skill endorsements

**Keybase**:
- Cryptographic identity proofs
- Linked accounts verification
- PGP key associations

## OPSEC Failures Demonstrated

### 1. Email Leak in Version Control
**Mistake**: Early GitHub commits before configuring privacy settings
**Exposure**: Personal email `akiernan2014@protonmail.com`
**Prevention**: Configure git privacy from day one, audit old commits

### 2. PDF Metadata
**Mistake**: Exported Google Docs PDF without scrubbing metadata
**Exposure**: Author name, creation tool (Google Docs)
**Prevention**: Use metadata scrubbing tools before publishing documents

### 3. Geographic Inconsistencies
**Mistake**: Different geographic signals create investigative leads
**Exposure**: Warsaw conference, Amsterdam hosting, Miami rumors
**Prevention**: Maintain consistent geographic story or accept increased exposure

### 4. Username Reuse
**Mistake**: Using similar usernames across platforms
**Exposure**: `alexkiernan`, `akiernan`, `@ak_cybersec` all linkable
**Prevention**: Use unique usernames per platform or accept linkability

## Why This Approach is "Scary"

**Not based on hunches** - Every step is:
- Documented with sources
- Cross-referenced across platforms
- Verified through multiple methods
- Built into evidence chain

**Single photo → complete profile**:
- Photo → Conference → Associates → Company → Domain → Email
- Each link verified and documented
- Creates undeniable narrative

**Exploits small mistakes**:
- Old commit with email
- PDF metadata
- Historical DNS records
- Username patterns

## Implementation Workflow

### Initial Investigation Checklist

- [ ] Define target and starting information
- [ ] Identify most reliable artifact (usually photo)
- [ ] Treat all initial claims as unverified
- [ ] Document everything with timestamps

### Automated Enumeration Checklist

- [ ] Reverse image search (Yandex, Google, Bing)
- [ ] Username enumeration (Sherlock/Maigret)
- [ ] Email search (if known)
- [ ] Social media username variants
- [ ] Domain searches (if company/org involved)

### Manual Deep-Dive Checklist

For each lead found:
- [ ] Platform profile analysis
- [ ] Connection/network mapping
- [ ] Historical content review
- [ ] Metadata extraction
- [ ] Cross-platform correlation

### Domain Investigation Checklist

- [ ] WHOIS lookup
- [ ] Historical DNS (SecurityTrails)
- [ ] Website source code review
- [ ] Google dorking for hidden files
- [ ] SSL certificate analysis
- [ ] Subdomain enumeration

### Metadata Analysis Checklist

- [ ] PDF documents - Author, Producer, dates
- [ ] Images - EXIF data, GPS coordinates
- [ ] Office documents - Author, company, revision history
- [ ] Email headers - routing, originating IPs
- [ ] Code repositories - commit history, contributor emails

### Reporting Checklist

- [ ] Separate verified facts from inferences
- [ ] List sources for each finding
- [ ] Assign confidence levels
- [ ] Document evidence chain
- [ ] Identify open questions
- [ ] Suggest next investigative steps

## Critical Success Factors

1. **Patience** - Don't skip steps for quick answers
2. **Documentation** - Record every finding with source and timestamp
3. **Verification** - Cross-reference findings across multiple sources
4. **Methodical Process** - Follow phases systematically
5. **Attention to Detail** - Small mistakes reveal big information

## Source
https://archive.ph/ux2bt (archived from Medium)
Original: https://preciousvincentct.medium.com/how-to-be-a-scary-osint-analyst-22d7a744c8ca

## Author
D4rk_Intel (Medium)
Published: October 2025
