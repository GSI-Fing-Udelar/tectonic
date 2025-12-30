import random
import time
from typing import Optional
import subprocess
import sys

try:
    from faker import Faker
except ImportError:
    # Auto-install faker if not available
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'faker'])
    from faker import Faker

fake = Faker('es_ES')

# ============================================================================
# SEEDING UTILITIES
# ============================================================================

def get_faker_instance(seed: Optional[int] = None, index: int = 0) -> Faker:
    faker_instance = Faker('es_ES')
    if seed is not None:
        derived_seed = seed + index
        Faker.seed(derived_seed)
        random.seed(derived_seed)
    return faker_instance


def seed_random(seed: Optional[int] = None, index: int = 0) -> None:
    if seed is not None:
        derived_seed = seed + index
        random.seed(derived_seed)
        Faker.seed(derived_seed)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def rnd_port(seed: Optional[int] = None, index: int = 0):
    """Generate a random port number (optionally seeded)."""
    faker_instance = get_faker_instance(seed, index)
    return faker_instance.port_number()

def rnd_seq(seed: Optional[int] = None, index: int = 0):
    """Generate a random sequence number (optionally seeded)."""
    if seed is not None:
        seed_random(seed, index)
    return random.randint(10000, 90000)

def rnd_user_agent(seed: Optional[int] = None, index: int = 0):
    """Generate a random user agent (optionally seeded)."""
    faker_instance = get_faker_instance(seed, index)
    return faker_instance.user_agent()

def now_ts():
    return time.time()

def generate_dns_transaction_id(seed: Optional[int] = None, index: int = 0) -> int:
    """
    Generate a random DNS transaction ID (16-bit).
    """
    if seed is not None:
        seed_random(seed, index)
    return random.randint(1, 65535)



def get_dns_port() -> int:
    """
    Get the standard DNS port number.
    
    Returns:
        int: DNS port (53)
    """
    return 53

def get_random_title(seed: Optional[int] = None, index: int = 0) -> str:
    """Generate a random title/catch phrase (optionally seeded)."""
    faker_instance = get_faker_instance(seed, index)
    return faker_instance.catch_phrase()

def get_company_name(seed: Optional[int] = None, index: int = 0) -> str:
    """Generate a random company name (optionally seeded)."""
    faker_instance = get_faker_instance(seed, index)
    return faker_instance.company()

def get_sentence(seed: Optional[int] = None, index: int = 0) -> str:
    """Generate a random sentence (optionally seeded)."""
    faker_instance = get_faker_instance(seed, index)
    return faker_instance.sentence()

def get_text(max_nb_chars: int = 200, seed: Optional[int] = None, index: int = 0) -> str:
    """Generate random text (optionally seeded)."""
    faker_instance = get_faker_instance(seed, index)
    return faker_instance.text(max_nb_chars=max_nb_chars)

def get_domain_name(subdomains: int = 1, seed: Optional[int] = None, index: int = 0) -> str:
    """Generate a random domain name (optionally seeded)."""
    faker_instance = get_faker_instance(seed, index)
    return faker_instance.domain_name(levels=subdomains)

def get_public_ip(seed: Optional[int] = None, index: int = 0) -> str:
    """Generate a random public IP (optionally seeded)."""
    faker_instance = get_faker_instance(seed, index)
    return faker_instance.ipv4_public()

def get_private_ip(seed: Optional[int] = None, index: int = 0) -> str:
    """Generate a random private IP (optionally seeded)."""
    faker_instance = get_faker_instance(seed, index)
    return faker_instance.ipv4_private()

def get_mac_address(seed: Optional[int] = None, index: int = 0) -> str:
    """Generate a random MAC address (optionally seeded)."""
    faker_instance = get_faker_instance(seed, index)
    return faker_instance.mac_address()

def get_random_time(base_time: float, distribution: str = "uniform", seed: Optional[int] = None, index: int = 0) -> float:
    """Generate a random time offset from base_time (optionally seeded)."""
    if seed is not None:
        seed_random(seed, index)
    
    if distribution == "uniform":
        return base_time + random.uniform(0, 0.0025)
    elif distribution == "normal":
        return base_time + random.normalvariate(0, 0.0025)
    elif distribution == "exponential":
        return base_time + random.exponential(0.0025)
    else:
        raise ValueError(f"Invalid distribution: {distribution}")