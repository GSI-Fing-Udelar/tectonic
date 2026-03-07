#
# Tectonic - An academic Cyber Range
# Copyright (C) 2024 Grupo de Seguridad Informática, Universidad de la República,
# Uruguay
#
# This file is part of Tectonic.
#
# Tectonic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tectonic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Tectonic.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Custom Jinja2 filters for Ansible that use Faker library
These filters allow generating fake data directly in Ansible playbooks
"""
try:
    from faker import Faker
except ImportError:
    Faker = None

import random
from ansible.errors import AnsibleFilterError

if Faker is None:
        raise AnsibleFilterError("faker library is required.")
fake_es = Faker('es_ES')
fake_en = Faker('en_US')

class FilterModule:
    # Global Faker instances (no seed here - will be set per call)
    """Ansible filter plugin for Faker - exposes all faker functions as Jinja2 filters"""
    
    def filters(self):
        return {
            # Personal data
            'faker_name': self.faker_name,
            'faker_email': self.faker_email,
            'faker_phone': self.faker_phone,
            'faker_address': self.faker_address,
            'faker_city': self.faker_city,
            'faker_country': self.faker_country,
            'faker_job': self.faker_job,
            
            # Companies
            'faker_company': self.faker_company,
            'faker_cif': self.faker_cif,
            
            # Text
            'faker_paragraph': self.faker_paragraph,
            'faker_sentence': self.faker_sentence,
            'faker_lorem_text': self.faker_lorem_text,
            
            # Dates and numbers
            'faker_date': self.faker_date,
            'faker_number': self.faker_number,
            'faker_color': self.faker_color,
            
            # Internet
            'faker_url': self.faker_url,
            'faker_ipv4': self.faker_ipv4,
            'faker_mac': self.faker_mac,
            'faker_user_agent': self.faker_user_agent,
            
            # Lists
            'faker_name_list': self.faker_name_list,
            'faker_company_list': self.faker_company_list,
            
            # Spanish documents
            'faker_dni': self.faker_dni,
            'faker_iban': self.faker_iban,
        }


    def faker_name(self, text='', locale='es', seed=None):
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

    def faker_company(self, text='', locale='es', seed=None):
        """Generate a random company name with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.company()

    def faker_email(self, text='', seed=None):
        """Generate a random email address with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.email()

    def faker_phone(self, text='', locale='es', seed=None):
        """Generate a random phone number with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.phone_number()

    def faker_address(self, text='', locale='es', seed=None):
        """Generate a random address with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.address()

    def faker_city(self, text='', locale='es', seed=None):
        """Generate a random city name with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.city()

    def faker_country(self, text='', locale='es', seed=None):
        """Generate a random country name with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.country()

    def faker_paragraph(self, text='', num_sentences=5, locale='es', seed=None):
        """Generate a random paragraph of text with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.paragraph(nb_sentences=num_sentences)

    def faker_sentence(self, text='', locale='es', seed=None):
        """Generate a random sentence with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.sentence()

    def faker_date(self, text='', seed=None):
        """Generate a random date in YYYY-MM-DD format with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return str(fake_es.date_between(start_date='-30y', end_date='today'))

    def faker_url(self, text='', seed=None):
        """Generate a random URL with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.url()

    def faker_ipv4(self, text='', seed=None):
        """Generate a random IPv4 address with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.ipv4()

    def faker_mac(self, text='', seed=None):
        """Generate a random MAC address with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.mac_address()

    def faker_user_agent(self, text='', seed=None):
        """Generate a random user agent string with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.user_agent()

    def faker_job(self, text='', locale='es', seed=None):
        """Generate a random job/profession name with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.job()

    def faker_color(self, text='', seed=None):
        """Generate a random color name with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.color_name()

    def faker_number(self, text='', minimum=1, maximum=1000, seed=None):
        """Generate a random number in range with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return random.randint(int(minimum), int(maximum))

    def faker_name_list(self, text='', count=5, locale='es', seed=None):
        """Generate a list of random names with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return [fake.name() for _ in range(int(count))]

    def faker_company_list(self, text='', count=3, locale='es', seed=None):
        """Generate a list of random companies with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return [fake.company() for _ in range(int(count))]

    def faker_dni(self, text='', seed=None):
        """Generate a random Spanish DNI (National ID) with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        number = random.randint(10000000, 99999999)
        letter = letters[number % 23]
        return f"{number}{letter}"

    def faker_cif(self, text='', seed=None):
        """Generate a random Spanish CIF (Company Tax ID) with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        initial_letter = random.choice('ABCDEFGHJNPQRSUVW')
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        final_letter = random.choice('ABCDEFGHIJ')
        return f"{initial_letter}{numbers}{final_letter}"

    def faker_iban(self, text='', seed=None):
        """Generate a random Spanish IBAN with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.iban()

    def faker_lorem_text(self, text='', num_words=50, seed=None):
        """Generate Lorem Ipsum text with optional seed"""
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.text(max_nb_chars=int(num_words) * 5)
