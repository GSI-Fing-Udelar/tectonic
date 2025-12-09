#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Custom Jinja2 filters for Ansible that use Faker library
These filters allow generating fake data directly in Ansible playbooks
"""

from faker import Faker
import random

# Global Faker instances (no seed here - will be set per call)
fake_es = Faker('es_ES')
fake_en = Faker('en_US')

def faker_name(text='', locale='es', seed=None):
    """
    Generate a random name
    
    Args:
        text: Dummy parameter (for pipe compatibility)
        locale: 'es' or 'en'
        seed: Random seed for reproducibility (optional)
    
    Usage:
        {{ '' | faker_name }}
        {{ '' | faker_name(locale='en') }}
        {{ '' | faker_name(seed=42) }}
        {{ '' | faker_name(locale='en', seed=42) }}
    """
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return fake.name()

def faker_company(text='', locale='es', seed=None):
    """Generate a random company name with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return fake.company()

def faker_email(text='', seed=None):
    """Generate a random email address with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    return fake_es.email()

def faker_phone(text='', locale='es', seed=None):
    """Generate a random phone number with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return fake.phone_number()

def faker_address(text='', locale='es', seed=None):
    """Generate a random address with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return fake.address()

def faker_city(text='', locale='es', seed=None):
    """Generate a random city name with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return fake.city()

def faker_country(text='', locale='es', seed=None):
    """Generate a random country name with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return fake.country()

def faker_paragraph(text='', num_sentences=5, locale='es', seed=None):
    """Generate a random paragraph of text with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return fake.paragraph(nb_sentences=num_sentences)

def faker_sentence(text='', locale='es', seed=None):
    """Generate a random sentence with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return fake.sentence()

def faker_date(text='', seed=None):
    """Generate a random date in YYYY-MM-DD format with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    return str(fake_es.date_between(start_date='-30y', end_date='today'))

def faker_url(text='', seed=None):
    """Generate a random URL with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    return fake_es.url()

def faker_ipv4(text='', seed=None):
    """Generate a random IPv4 address with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    return fake_es.ipv4()

def faker_mac(text='', seed=None):
    """Generate a random MAC address with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    return fake_es.mac_address()

def faker_user_agent(text='', seed=None):
    """Generate a random user agent string with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    return fake_es.user_agent()

def faker_job(text='', locale='es', seed=None):
    """Generate a random job/profession name with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return fake.job()

def faker_color(text='', seed=None):
    """Generate a random color name with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    return fake_es.color_name()

def faker_number(text='', minimum=1, maximum=1000, seed=None):
    """Generate a random number in range with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    return random.randint(int(minimum), int(maximum))

def faker_name_list(text='', count=5, locale='es', seed=None):
    """Generate a list of random names with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return [fake.name() for _ in range(int(count))]

def faker_company_list(text='', count=3, locale='es', seed=None):
    """Generate a list of random companies with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    fake = fake_es if locale == 'es' else fake_en
    return [fake.company() for _ in range(int(count))]

def faker_dni(text='', seed=None):
    """Generate a random Spanish DNI (National ID) with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    number = random.randint(10000000, 99999999)
    letter = letters[number % 23]
    return f"{number}{letter}"

def faker_cif(text='', seed=None):
    """Generate a random Spanish CIF (Company Tax ID) with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    
    initial_letter = random.choice('ABCDEFGHJNPQRSUVW')
    numbers = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    final_letter = random.choice('ABCDEFGHIJ')
    return f"{initial_letter}{numbers}{final_letter}"

def faker_iban(text='', seed=None):
    """Generate a random Spanish IBAN with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    return fake_es.iban()

def faker_lorem_text(text='', num_words=50, seed=None):
    """Generate Lorem Ipsum text with optional seed"""
    if seed is not None:
        Faker.seed(int(seed))
        random.seed(int(seed))
    return fake_es.text(max_nb_chars=int(num_words) * 5)

class FilterModule:
    """Ansible filter plugin for Faker - exposes all faker functions as Jinja2 filters"""
    
    def filters(self):
        return {
            # Personal data
            'faker_name': faker_name,
            'faker_email': faker_email,
            'faker_phone': faker_phone,
            'faker_address': faker_address,
            'faker_city': faker_city,
            'faker_country': faker_country,
            'faker_job': faker_job,
            
            # Companies
            'faker_company': faker_company,
            'faker_cif': faker_cif,
            
            # Text
            'faker_paragraph': faker_paragraph,
            'faker_sentence': faker_sentence,
            'faker_lorem_text': faker_lorem_text,
            
            # Dates and numbers
            'faker_date': faker_date,
            'faker_number': faker_number,
            'faker_color': faker_color,
            
            # Internet
            'faker_url': faker_url,
            'faker_ipv4': faker_ipv4,
            'faker_mac': faker_mac,
            'faker_user_agent': faker_user_agent,
            
            # Lists
            'faker_name_list': faker_name_list,
            'faker_company_list': faker_company_list,
            
            # Spanish documents
            'faker_dni': faker_dni,
            'faker_iban': faker_iban,
        }
