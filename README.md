# MAI - Model Academic Impact Analysis System

MAI (Model Academic Impact Analysis) is an automated academic literature and patent data collection system focused on analyzing the academic impact and research trends of different AI models.

## Project Overview

This system collects papers and patents related to specific AI models by crawling academic databases such as Scopus and ScienceDirect, as well as the Google Patents database, to build academic impact profiles for models.

## Core Features

### 1. Academic Paper Data Collection
- **Paper Search**: Search for relevant papers based on model full names and abbreviations across multiple academic databases
- **Citation Relationships**: Automatically retrieve citing papers to build citation networks
- **Data Source Support**: Scopus, ScienceDirect
- **Field Extraction**: Automatically extract detailed information including authors, institutions, abstracts, keywords, research areas, etc.

### 2. Patent Data Collection
- **Patent Search**: Search for model-related patents in Google Patents
- **Patent Analysis**: Extract basic patent information, inventors, assignees, claims, etc.
- **Citation Relationships**: Retrieve forward and backward patent citations

### 3. Database Storage
- **MongoDB**: Uses MongoDB as the primary data storage solution
- **Data Classification**: Separately stores model information, paper data, patent data, and citation relationships
- **Deduplication**: Automatically identifies and handles duplicate data

## File Structure

```
MAI/
├── paper_spider_final.py      # Main paper crawler
├── paper_spider_final1.py     # Backup version of paper crawler
├── paper_ref_final.py         # Paper citation collection
├── paper_ref_final1.py        # Backup version of paper citation collection
├── patent_spider_final.py     # Main patent crawler
├── patent_spider_final1.py    # Backup version of patent crawler
├── patent_ref_final.py        # Patent citation collection
└── patent_ref_final1.py       # Backup version of patent citation collection
```

## Main Module Description

### Paper Crawler Module (paper_spider_final.py)
- Supports both full name and abbreviation search modes
- Data collection by year ranges
- Automatic handling of API quota limits and access frequency
- Intelligent relevance judgment between papers and models
- Real-time progress saving with resume capability

### Patent Crawler Module (patent_spider_final.py)
- Patent search based on Google Patents API
- Batch collection of patent data by time ranges
- Extraction of complete detailed patent information
- Automatic handling of patent citation relationships

### Citation Collection Modules
- **paper_ref_final.py**: Collects citing papers
- **patent_ref_final.py**: Collects patent citations
- Supports incremental updates to avoid duplicate collection

## Technical Features

### 1. Intelligent Search Strategy
- **Dual-mode Search**: Combines full names and abbreviations for searching
- **Relevance Judgment**: For abbreviation search results, determines relevance to models by analyzing references
- **Subject Filtering**: Filters papers from specific fields like environmental, agricultural, earth sciences, and decision sciences

### 2. Data Quality Assurance
- **Deduplication Mechanism**: Deduplication based on unique identifiers like EID, DOI
- **Error Handling**: Comprehensive exception handling mechanisms ensuring program stability
- **Data Validation**: Format validation and integrity checking of collected data

### 3. Performance Optimization
- **Concurrency Control**: Strict control of API access frequency to avoid being blocked
- **Resume Capability**: Supports resuming collection from the last position after program interruption
- **Configuration Files**: Uses configuration files to record collection progress
- **Batch Processing**: Automatic batch processing for large data volumes

### 4. Scalability
- **Modular Design**: Functional modules are relatively independent, easy to maintain and extend
- **Multi-version Support**: Provides backup versions supporting different collection strategies
- **Flexible Configuration**: Supports various database connections and collection parameter configurations

## Database Design

### Main Collections
- **model**: Stores basic AI model information (full name, abbreviation, etc.)
- **Paper**: Stores detailed paper information
- **PaperCite**: Stores paper citation data
- **Patent**: Stores patent information
- **PatentCite**: Stores patent citation relationships

### Data Relationships
- Each model is associated with multiple related papers and patents
- Papers and patents maintain their respective citation networks
- Supports complex academic impact analysis queries

## Use Cases

1. **Academic Research**: Analyze the academic impact and development trends of specific AI models
2. **Technical Investigation**: Understand the application of a model in academia and industry
3. **Competitive Analysis**: Compare the academic performance and patent landscape of different models
4. **Trend Prediction**: Predict technology development directions based on citation network analysis

## Important Notes

1. **API Limitations**: Requires valid Scopus/ScienceDirect API keys
2. **Access Frequency**: Strictly adhere to access frequency limits of each platform
3. **Data Compliance**: Ensure data collection complies with the terms of use of each platform
4. **Storage Space**: Large-scale collection requires sufficient database storage space

## Installation & Setup

### Prerequisites
- Python 3.x
- MongoDB database (running and accessible)
- Valid API keys for Scopus/ScienceDirect
- Required Python packages: requests, pymongo, beautifulsoup4, dateutil, lxml

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MAI
   ```

2. **Install dependencies**
   ```bash
   pip install requests pymongo beautifulsoup4 python-dateutil lxml urllib3
   ```

3. **Database Setup**
   - Ensure MongoDB is running
   - Update database connection parameters in the scripts:
     ```python
     ip = "your_mongodb_ip"  # Default: "172.21.213.33"
     port = 27017
     dbName = "ModelDB"
     ```

4. **API Key Configuration**
   - Create API key files:
     ```
     scopus/apiKey_cry.txt  # For main version
     ../scopus/apiKey_cry.txt  # For backup versions
     ```
   - Add your Scopus/ScienceDirect API keys (one per line)

5. **Configuration Directories**
   Create necessary directories for configuration files:
   ```bash
   mkdir configure
   mkdir patent  # For patent crawler configuration
   ```

## Usage Instructions

### Running the System

The system consists of four main components that should be run in sequence:

#### 1. Paper Data Collection

**Main Version:**
```bash
python paper_spider_final.py
```

**Backup Version (alternative database/settings):**
```bash
python paper_spider_final1.py
```

**Features:**
- Searches for papers using model full names and abbreviations
- Supports both Scopus and ScienceDirect APIs
- Automatically handles rate limiting and API quotas
- Saves progress in `configure/paperSearch.conf` or `configure/paperSearch1.conf`

#### 2. Paper Citation Collection

**Main Version:**
```bash
python paper_ref_final.py
```

**Backup Version:**
```bash
python paper_ref_final1.py
```

**Features:**
- Collects citing papers for already collected papers
- Updates citation counts and relationships
- Saves progress in `configure/paperRef.conf` or `configure/paperRef1.conf`

#### 3. Patent Data Collection

**Main Version:**
```bash
python patent_spider_final.py
```

**Backup Version:**
```bash
python patent_spider_final1.py
```

**Features:**
- Searches Google Patents for model-related patents
- Extracts detailed patent information
- Saves progress in `patent/patent.conf` or `patent/patent1.conf`

#### 4. Patent Citation Collection

**Main Version:**
```bash
python patent_ref_final.py
```

**Backup Version:**
```bash
python patent_ref_final1.py
```

**Features:**
- Collects forward and backward patent citations
- Updates patent citation relationships
- Saves progress in `configure/patentRef.conf` or `configure/patentRef1.conf`

### Configuration Files

The system uses configuration files to track progress and enable resume functionality:

- **Paper Collection**: `configure/paperSearch.conf`
  ```
  model_id
  start_year
  end_year
  current_count
  search_type (f/a)
  data_source (scopus/sciDir)
  ```

- **Paper Citation**: `configure/paperRef.conf`
  ```
  model_id
  paper_id
  ```

- **Patent Collection**: `patent/patent.conf`
  ```
  model_id
  start_date
  end_date
  current_count
  ```

- **Patent Citation**: `configure/patentRef.conf`
  ```
  patent_id
  ```

### Monitoring and Troubleshooting

1. **Progress Monitoring**: Check configuration files to see current progress
2. **Log Output**: Monitor console output for real-time status
3. **Error Handling**: The system automatically retries failed requests
4. **Resume Capability**: Stop and restart scripts anytime - they will resume from the last saved position

### Data Verification

After running the scripts, verify data collection in MongoDB:

```javascript
// Connect to MongoDB and check collections
use ModelDB
db.model.count()      // Check model count
db.Paper.count()      // Check paper count
db.PaperCite.count()  // Check paper citation count
db.Patent.count()     // Check patent count
db.PatentCite.count() // Check patent citation count
```

## Best Practices

1. **Run in Sequence**: Execute paper collection before citation collection
2. **Monitor API Limits**: Keep track of daily/weekly API quotas
3. **Backup Configuration**: Regularly backup configuration files
4. **Database Maintenance**: Monitor database storage and performance
5. **Error Logs**: Check for and address any error messages in the output

---

This project provides complete data collection and analysis infrastructure for academic research and technical analysis, supporting large-scale, automated academic impact analysis work.