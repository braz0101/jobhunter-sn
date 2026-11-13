"""
Extracteur de compétences depuis un texte d'offre d'emploi.
Approche : dictionnaire normalisé + regex, sans dépendances ML lourdes.
Optimisé pour le marché IT sénégalais (FR + EN).
"""

import re
from unidecode import unidecode
from typing import List, Set

# ─────────────────────────────────────────────────────────────────────────────
# DICTIONNAIRE MAÎTRE : skill_canonical → [variantes / alias]
# ─────────────────────────────────────────────────────────────────────────────
SKILLS_DICT: dict[str, list[str]] = {

    # ── Systèmes d'exploitation ──────────────────────────────────────────────
    "linux":          ["linux", "ubuntu", "debian", "centos", "rhel", "fedora", "kali",
                       "parrot", "archlinux", "alpine", "shell linux"],
    "windows_server": ["windows server", "windows srv", "win server", "ws 2019", "ws 2022",
                       "serveur windows", "server 2016", "server 2019", "server 2022"],
    "bash":           ["bash", "shell scripting", "shell script", "bash scripting", "zsh", "sh"],

    # ── Active Directory & Identité ──────────────────────────────────────────
    "active_directory": ["active directory", "active-directory", "ad ds", "ldap", "annuaire",
                         "domain controller", "contrôleur de domaine"],
    "dns":              ["dns", "bind9", "résolution de noms", "name server", "zone dns"],
    "dhcp":             ["dhcp", "attribution ip", "adresse ip dynamique"],
    "gpo":              ["gpo", "group policy", "stratégie de groupe", "gpmc"],

    # ── Réseau & Infrastructure ──────────────────────────────────────────────
    "cisco":       ["cisco", "ios", "ccna", "ccnp", "ccie", "catalyst", "nexus", "asr"],
    "routage":     ["routage", "routing", "bgp", "ospf", "eigrp", "rip", "mpls", "isis"],
    "vlan":        ["vlan", "802.1q", "trunking", "segmentation réseau", "inter-vlan"],
    "vpn":         ["vpn", "ipsec", "ssl vpn", "openvpn", "wireguard", "l2tp",
                    "tunnel vpn", "accès distant sécurisé"],
    "pfsense":     ["pfsense", "pare-feu", "firewall", "fortinet", "fortigate",
                    "cisco asa", "checkpoint", "juniper srx"],
    "wireshark":   ["wireshark", "analyse réseau", "capture paquets", "tcpdump", "sniffing"],
    "tcp_ip":      ["tcp/ip", "tcp ip", "protocoles réseau", "ipv4", "ipv6", "nat", "pat"],

    # ── Supervision / Monitoring ─────────────────────────────────────────────
    "nagios":    ["nagios", "nagios xi", "nagios core"],
    "zabbix":    ["zabbix", "supervision réseau", "monitoring réseau", "noc"],
    "grafana":   ["grafana", "prometheus", "elk", "elasticsearch", "kibana", "logstash",
                  "splunk", "datadog"],

    # ── Virtualisation ───────────────────────────────────────────────────────
    "vmware":       ["vmware", "vsphere", "esxi", "vcenter", "vsan"],
    "virtualisation": ["virtualisation", "virtualbox", "hyper-v", "hyperv", "kvm", "xen",
                       "proxmox", "qemu", "vm", "machine virtuelle"],

    # ── Conteneurs & Orchestration ───────────────────────────────────────────
    "docker":      ["docker", "conteneur", "container", "containerisation", "dockerfile",
                    "docker compose", "docker swarm"],
    "kubernetes":  ["kubernetes", "k8s", "helm", "kubectl", "pods", "deployment", "openshift",
                    "orchestration conteneurs"],

    # ── Cloud ────────────────────────────────────────────────────────────────
    "aws":    ["aws", "amazon web services", "ec2", "s3", "lambda", "rds", "iam",
               "vpc", "route53", "cloudfront", "eks", "ecs"],
    "azure":  ["azure", "microsoft azure", "azure ad", "azure devops", "aks"],
    "gcp":    ["gcp", "google cloud", "gke", "bigquery", "cloud run"],

    # ── DevOps / CI-CD ───────────────────────────────────────────────────────
    "devops":    ["devops", "sre", "platform engineer", "site reliability"],
    "cicd":      ["ci/cd", "pipeline ci", "jenkins", "gitlab ci", "github actions",
                  "travis ci", "circle ci", "drone", "argocd", "tekton"],
    "terraform": ["terraform", "infrastructure as code", "iac", "pulumi"],
    "ansible":   ["ansible", "playbook ansible", "automation", "chef", "puppet", "salt"],
    "git":       ["git", "github", "gitlab", "bitbucket", "versioning", "contrôle version"],

    # ── Cybersécurité ────────────────────────────────────────────────────────
    "metasploit": ["metasploit", "msfconsole", "exploitation", "payload", "exploit"],
    "nessus":     ["nessus", "tenable", "scan vulnérabilités", "vulnerability scan",
                   "openvas", "qualys"],
    "nmap":       ["nmap", "scan ports", "port scan", "reconnaissance réseau"],
    "pentest":    ["pentest", "test intrusion", "penetration testing", "red team", "ctf",
                   "ethical hacking", "test de pénétration", "audit sécurité",
                   "blue team", "purple team"],
    "soc":        ["soc", "centre opérations sécurité", "siem", "analyste sécurité",
                   "security analyst", "incident response", "réponse incident"],
    "freeradius": ["freeradius", "radius", "802.1x", "authentification réseau",
                   "nac", "contrôle accès réseau"],
    "cybersecurite": ["cybersécurité", "cybersecurity", "sécurité informatique",
                      "sécurité réseau", "infosec", "information security"],
    "ids_ips":    ["ids", "ips", "snort", "suricata", "détection intrusion", "waf"],
    "cryptographie": ["cryptographie", "pki", "ssl", "tls", "https", "chiffrement",
                      "openssl", "certificat"],

    # ── Data Engineering ─────────────────────────────────────────────────────
    "python":       ["python", "python3", "python 3", "django", "flask", "fastapi"],
    "sql":          ["sql", "requête sql", "optimisation sql", "stored procedure",
                     "procédure stockée"],
    "postgresql":   ["postgresql", "postgres", "psql"],
    "mysql":        ["mysql", "mariadb"],
    "oracle":       ["oracle", "oracle db", "plsql", "pl/sql"],
    "mongodb":      ["mongodb", "nosql", "redis", "cassandra", "elasticsearch"],
    "hadoop":       ["hadoop", "hdfs", "mapreduce", "hive", "hbase", "pig"],
    "spark":        ["spark", "apache spark", "pyspark", "databricks"],
    "airflow":      ["airflow", "apache airflow", "dag", "orchestration données"],
    "etl":          ["etl", "elt", "pipeline données", "ingestion données",
                     "data pipeline", "data engineering", "ingestion"],
    "powerbi":      ["power bi", "powerbi", "power-bi", "microsoft bi"],
    "tableau":      ["tableau", "looker", "metabase", "superset", "qlikview",
                     "visualisation données", "data visualization"],

    # ── IA / Machine Learning ────────────────────────────────────────────────
    "machine_learning": ["machine learning", "ml", "apprentissage automatique",
                         "modèle prédictif", "apprentissage supervisé"],
    "deep_learning":    ["deep learning", "dl", "réseau de neurones", "neural network",
                         "apprentissage profond"],
    "tensorflow":       ["tensorflow", "tf", "keras", "tensorflow keras"],
    "scikit_learn":     ["scikit-learn", "sklearn", "scikit learn"],
    "pytorch":          ["pytorch", "torch"],
    "nlp":              ["nlp", "traitement langage naturel", "natural language processing",
                         "transformers", "bert", "llm", "gpt"],
    "lstm_gru":         ["lstm", "gru", "bigru", "bilstm", "rnn",
                         "réseau récurrent", "recurrent neural network"],
    "random_forest":    ["random forest", "gradient boosting", "xgboost", "lightgbm",
                         "catboost", "decision tree"],
    "mlops":            ["mlops", "mlflow", "kubeflow", "bentoml", "ray", "vertex ai"],

    # ── Télécommunications ───────────────────────────────────────────────────
    "4g_lte":   ["4g", "lte", "lte-a", "réseau mobile 4g", "long term evolution"],
    "5g":       ["5g", "nr", "5g core", "5g ran", "5g standalone", "sa 5g"],
    "voip":     ["voip", "toip", "sip", "téléphonie ip", "ip telephony"],
    "asterisk": ["asterisk", "pbx", "ipbx", "freepbx", "trunk sip", "ivr"],
    "radio":    ["rsrp", "rsrq", "sinr", "cqi", "drive test", "gnettrack",
                 "g-nettrack", "atoll", "propagation radio", "planning radio",
                 "optimisation radio", "rf engineer"],
    "sdn_nfv":  ["sdn", "nfv", "openflow", "ovs", "openvswitch", "opendaylight",
                 "onos", "network slicing", "vnf"],

    # ── Support IT ───────────────────────────────────────────────────────────
    "support_n1n2": ["support n1", "support n2", "support n3", "helpdesk",
                     "help desk", "assistance technique", "support utilisateurs",
                     "it support", "service desk"],
    "itsm":         ["itsm", "itil", "glpi", "servicenow", "remedy", "jira service",
                     "gestion incidents", "ticketing"],

    # ── Langages & Frameworks ────────────────────────────────────────────────
    "javascript":  ["javascript", "js", "node.js", "nodejs", "express", "typescript", "ts"],
    "react":       ["react", "reactjs", "react.js", "next.js", "nextjs"],
    "java":        ["java", "spring", "spring boot", "jee", "jakarta ee", "jvm"],
    "php":         ["php", "laravel", "symfony", "wordpress"],
    "csharp":      ["c#", "csharp", ".net", "asp.net", "dotnet"],
    "cpp":         ["c++", "c/c++", "language c", "programmation c"],

    # ── Méthodes & Gestion de projet ─────────────────────────────────────────
    "agile":        ["agile", "scrum", "kanban", "sprint", "jira", "confluence"],
    "gestion_projet": ["gestion de projet", "chef de projet", "project management",
                       "pmp", "prince2"],
}

# ─────────────────────────────────────────────────────────────────────────────
# NORMALISATION
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Minuscules + suppression accents + collapse espaces."""
    return re.sub(r'\s+', ' ', unidecode(text).lower().strip())


def _build_lookup() -> dict[str, str]:
    """
    Construit un dictionnaire inversé : alias_normalisé → skill_canonical.
    Exemple : "active-directory" → "active_directory"
    """
    lookup = {}
    for canonical, aliases in SKILLS_DICT.items():
        for alias in aliases:
            norm = _normalize(alias)
            lookup[norm] = canonical
    return lookup


# Pré-compilation unique au démarrage
_LOOKUP: dict[str, str] = _build_lookup()
_SORTED_ALIASES: list[tuple[str, str]] = sorted(
    _LOOKUP.items(), key=lambda x: len(x[0]), reverse=True  # plus long en premier
)


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTEUR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def extract_skills(text: str) -> List[str]:
    """
    Extrait les compétences canoniques depuis un texte d'offre d'emploi.

    Stratégie :
    1. Normaliser le texte source
    2. Parcourir les alias du plus long au plus court (évite les sous-chaînes)
    3. Marquer les positions consommées pour éviter les double-comptages

    Returns:
        Liste de skills canoniques dédupliqués, ex: ["docker", "python", "linux"]
    """
    if not text:
        return []

    normalized = _normalize(text)
    found_canonicals: Set[str] = set()
    consumed_positions: set = set()

    for alias, canonical in _SORTED_ALIASES:
        # Recherche de l'alias en tant que mot complet (boundary word)
        pattern = r'(?<![a-z0-9_/-])' + re.escape(alias) + r'(?![a-z0-9_/-])'
        for match in re.finditer(pattern, normalized):
            start, end = match.start(), match.end()
            # Vérifie qu'aucune position n'est déjà consommée
            positions = set(range(start, end))
            if not positions.intersection(consumed_positions):
                found_canonicals.add(canonical)
                consumed_positions.update(positions)

    return sorted(found_canonicals)


def extract_job_type(text: str) -> str | None:
    """
    Détecte le type de contrat dans le titre ou description d'une offre.
    Returns: 'stage', 'pfe', 'cdi', 'cdd', 'alternance', 'freelance', ou None
    """
    normalized = _normalize(text)

    patterns = [
        (r'\bpfe\b|fin d.etudes?|memoire|these', 'pfe'),
        (r'\bstage\b|stagiaire|internship|intern\b', 'stage'),
        (r'\balternance\b|alternant|apprentissage|apprenti\b', 'alternance'),
        (r'\bcdd\b|contrat a duree determinee', 'cdd'),
        (r'\bcdi\b|contrat a duree indeterminee', 'cdi'),
        (r'\bfreelance\b|consultant independant|independent', 'freelance'),
    ]

    for pattern, job_type in patterns:
        if re.search(pattern, normalized):
            return job_type
    return None


def extract_location_type(text: str) -> bool:
    """Retourne True si l'offre mentionne du remote."""
    normalized = _normalize(text)
    return bool(re.search(r'\bteletravail\b|remote\b|\ba distance\b|full.?remote|work from home', normalized))
