"""
Profil utilisateur pour le matching.
Ce fichier définit les compétences, rôles cibles et préférences d'Ibrahima FALL.
Modifiable pour adapter à tout autre profil.
"""

USER_PROFILE = {
    "name": "Ibrahima FALL",
    "email": "ibrahimafall3@esp.sn",
    "formation": "Master 2 SRT – ESP/UCAD",
    "niveau": "junior",  # junior / mid / senior
    "localisation": "Dakar, Sénégal",

    # ─── COMPÉTENCES TECHNIQUES ────────────────────────────────
    # Normalisées en minuscules pour le matching
    "competences": [
        # Systèmes & réseaux
        "linux", "ubuntu", "centos", "debian",
        "windows server", "active directory", "dns", "dhcp", "gpo",
        "docker", "nagios", "zabbix",
        "cisco", "pfsense", "vlan", "routage", "bgp", "ospf",
        "virtualisation", "vmware", "proxmox",
        "ipv4", "ipv6", "tcp/ip",

        # Cybersécurité
        "metasploit", "nessus", "nmap", "wireshark",
        "freeradius", "802.1x", "pentest", "test intrusion",
        "cybersécurité", "audit sécurité", "soc",
        "ids", "ips", "snort",

        # Cloud & DevOps
        "docker", "aws", "ec2", "s3",
        "kubernetes", "terraform", "ansible",
        "ci/cd", "github actions", "gitlab ci", "jenkins",
        "devops", "sre",

        # Data & IA
        "python", "pandas", "numpy", "scipy",
        "tensorflow", "keras", "scikit-learn",
        "machine learning", "deep learning",
        "lstm", "gru", "bigru", "rnn",
        "random forest", "gradient boosting", "xgboost",
        "hadoop", "spark", "hive",
        "airflow", "etl", "pipeline données",
        "postgresql", "mysql", "sql",
        "power bi", "tableau", "visualisation données",

        # Télécoms
        "asterisk", "sip", "voip", "toip", "pbx",
        "4g", "5g", "lte", "nr",
        "rsrp", "rsrq", "sinr", "cqi",
        "gnettrack", "drive test", "atoll",
        "open5gs", "ueransim", "sdn", "nfv",

        # Support IT
        "support n1", "support n2", "helpdesk",
        "itsm", "itil", "glpi",

        # Langages
        "python", "javascript", "typescript",
        "next.js", "react", "node.js",
        "bash", "shell",
    ],

    # ─── RÔLES CIBLES (pour le titre-matching) ─────────────────
    "roles_cibles": [
        # Priorité 1 – Cœur de métier
        "ingénieur systèmes réseaux", "administrateur systèmes",
        "ingénieur réseau", "architecte réseau",
        "ingénieur télécoms", "ingénieur infrastructure",

        # Priorité 2 – Cybersécurité
        "ingénieur cybersécurité", "analyste soc",
        "pentester", "consultant sécurité",

        # Priorité 3 – Cloud / DevOps
        "ingénieur cloud", "ingénieur devops",
        "site reliability engineer", "platform engineer",

        # Priorité 4 – Data / IA
        "data engineer", "ingénieur données",
        "ingénieur ia", "ml engineer",
        "data analyst", "noc engineer",

        # Priorité 5 – Support / IT généraliste
        "technicien support", "support informatique",
        "administrateur it", "consultant it",

        # Mots-clés généraux
        "réseaux", "télécoms", "systèmes", "informatique",
        "cloud", "sécurité", "data", "stage", "pfe",
    ],

    # ─── PRÉFÉRENCES GÉOGRAPHIQUES ─────────────────────────────
    "localisation_preferee": ["dakar", "sénégal", "senegal"],
    "remote_ok": True,
    "afrique_ok": True,  # Afrique francophone acceptée

    # ─── TYPES DE CONTRAT ──────────────────────────────────────
    "types_contrat": ["stage", "pfe", "fin d'études", "cdi", "cdd", "alternance", "freelance"],

    # ─── SALAIRE ────────────────────────────────────────────────
    "salaire_min_xof": 0,  # Flexible pour les stages
    "experience_annees": 1,
}
