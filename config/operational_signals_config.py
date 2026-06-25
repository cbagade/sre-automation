"""Configuration for Operational Signals data fetching."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Git Repository Configuration
# Set these in .env file:
# OPS_SIGNALS_GIT_URL - Base URL to your git repository
# OPS_SIGNALS_GIT_BRANCH - Branch name (default: main)
# OPS_SIGNALS_GIT_TOKEN - Authentication token (optional, for private repos)

GIT_CONFIG = {
    # Base git URL (without branch)
    # Example: "https://raw.githubusercontent.com/your-org/operational-signals"
    # The system will append: /{branch}/{region}/{date}/{timeslot}/{filename}.json
    "git_url": os.getenv("OPS_SIGNALS_GIT_URL", "https://raw.githubusercontent.com/your-org/operational-signals"),
    
    # Branch name
    "branch": os.getenv("OPS_SIGNALS_GIT_BRANCH", "main"),
    
    # Authentication token (optional, for private repositories)
    # For GitHub: Personal Access Token (PAT)
    # For GitLab: Personal Access Token or Deploy Token
    # For Bitbucket: App Password
    "token": os.getenv("OPS_SIGNALS_GIT_TOKEN", None),
}

# Available regions/MZRs
# Update this list based on your infrastructure
AVAILABLE_REGIONS = [
    "Tokyo-Staging",
    "TOR",
    "SAO",
    "Dallas",
    "WDC",
    "TOK",
    "MAD",
    "PAR",
    "FRA",
]

# JSON files to fetch from git repository
# These files should exist in the path: {region}/{date}/{timeslot}/{filename}
JSON_FILES = [
    "active_critical_immediate_alerts.json",
    "clusters_needing_attention.json",
    "esxi_hosts_needing_attention.json",
    "management_vms_needing_attention.json",
    "nfs_datastores_needing_attention.json",
    "nsx_alarms.json",
    "provider_vdcs_needing_attention.json",
    "vcenter_alarms.json",
    "vcloud_director_cells_needing_attention.json",
    "vsan_clusters_needing_attention.json",
]

# Cache configuration
CACHE_CONFIG = {
    # Directory to store cache files
    "cache_dir": "data/cache/operational_signals",
    
    # Cache expiration in hours (optional, not currently used)
    "cache_expiration_hours": 24,
}

# Made with Bob
