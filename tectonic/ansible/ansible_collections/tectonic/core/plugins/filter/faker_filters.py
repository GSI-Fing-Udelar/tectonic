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
        """
        Generate a random company name with optional seed

        Args:
            text: Dummy parameter (for pipe compatibility)
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated company name.

        Usage:
            {{ '' | faker_company }}
            {{ '' | faker_company(locale='en') }}
            {{ '' | faker_company(seed=42) }}
            {{ '' | faker_company(locale='en', seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.company()

    def faker_email(self, text='', seed=None):
        """
        Generate a random email address with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated name.

        Usage:
            {{ '' | faker_email }}
            {{ '' | faker_email(locale='en') }}
            {{ '' | faker_email(seed=42) }}
            {{ '' | faker_email(locale='en', seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.email()

    def faker_phone(self, text='', locale='es', seed=None):
        """
        Generate a random phone number with optional seed

        Args:
            text: Dummy parameter (for pipe compatibility)
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated number phone.

        Usage:
            {{ '' | faker_phone }}
            {{ '' | faker_phone(locale='en') }}
            {{ '' | faker_phone(seed=42) }}
            {{ '' | faker_phone(locale='en', seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.phone_number()

    def faker_address(self, text='', locale='es', seed=None):
        """
        Generate a random address with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated address.

        Usage:
            {{ '' | faker_address }}
            {{ '' | faker_address(locale='en') }}
            {{ '' | faker_address(seed=42) }}
            {{ '' | faker_address(locale='en', seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.address()

    def faker_city(self, text='', locale='es', seed=None):
        """
        Generate a random city name with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated city.

        Usage:
            {{ '' | faker_city }}
            {{ '' | faker_city(locale='en') }}
            {{ '' | faker_city(seed=42) }}
            {{ '' | faker_city(locale='en', seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.city()

    def faker_country(self, text='', locale='es', seed=None):
        """
        Generate a random country name with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated country.

        Usage:
            {{ '' | faker_country }}
            {{ '' | faker_country(locale='en') }}
            {{ '' | faker_country(seed=42) }}
            {{ '' | faker_country(locale='en', seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.country()

    def faker_paragraph(self, text='', num_sentences=5, locale='es', seed=None):
        """
        Generate a random paragraph of text with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            num_sentences: Number of sentences
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated paragraph.

        Usage:
            {{ '' | faker_paragraph }}
            {{ '' | faker_paragraph(num_sentences=10) }}
            {{ '' | faker_paragraph(locale='en') }}
            {{ '' | faker_paragraph(seed=42) }}
            {{ '' | faker_paragraph(num_sentences=10, locale='en', seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.paragraph(nb_sentences=num_sentences)

    def faker_sentence(self, text='', locale='es', seed=None):
        """
        Generate a random sentence with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated sentence.

        Usage:
            {{ '' | faker_sentence }}
            {{ '' | faker_sentence(locale='en') }}
            {{ '' | faker_sentence(seed=42) }}
            {{ '' | faker_sentence(locale='en', seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.sentence()

    def faker_date(self, text='', seed=None):
        """
        Generate a random date in YYYY-MM-DD format with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated date.

        Usage:
            {{ '' | faker_date }}
            {{ '' | faker_date(seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return str(fake_es.date_between(start_date='-30y', end_date='today'))

    def faker_url(self, text='', seed=None):
        """
        Generate a random URL with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated URL.

        Usage:
            {{ '' | faker_url }}
            {{ '' | faker_url(seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.url()

    def faker_ipv4(self, text='', seed=None):
        """
        Generate a random IPv4 address with optional seed

        Args:
            text: Dummy parameter (for pipe compatibility)
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated IPv4 address.

        Usage:
            {{ '' | faker_ipv4 }}
            {{ '' | faker_ipv4(seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.ipv4()

    def faker_mac(self, text='', seed=None):
        """
        Generate a random MAC address with optional seed

        Args:
            text: Dummy parameter (for pipe compatibility)
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated MAC address.

        Usage:
            {{ '' | faker_mac }}
            {{ '' | faker_mac(seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.mac_address()

    def faker_user_agent(self, text='', seed=None):
        """
        Generate a random user agent string with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated user agent.

        Usage:
            {{ '' | faker_user_agent }}
            {{ '' | faker_user_agent(seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.user_agent()

    def faker_job(self, text='', locale='es', seed=None):
        """
        Generate a random job/profession name with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated job/profession name.

        Usage:
            {{ '' | faker_job }}
            {{ '' | faker_job(locale='en') }}
            {{ '' | faker_job(seed=42) }}
            {{ '' | faker_job(locale='en', seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return fake.job()

    def faker_color(self, text='', seed=None):
        """
        Generate a random color name with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated color.

        Usage:
            {{ '' | faker_color }}
            {{ '' | faker_color(seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.color_name()

    def faker_number(self, text='', minimum=1, maximum=1000, seed=None):
        """
        Generate a random number in range with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            minimum: Smallest number in the range
            maximum: Maximum number in the range
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated number.

        Usage:
            {{ '' | faker_number }}
            {{ '' | faker_number(minimum=5) }}
            {{ '' | faker_number(maximum=570) }}
            {{ '' | faker_number(seed=42) }}
            {{ '' | faker_number(minimum=5, maximum=570, seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return random.randint(int(minimum), int(maximum))

    def faker_name_list(self, text='', count=5, locale='es', seed=None):
        """
        Generate a list of random names with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            count: Number of names in the list
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated name list.

        Usage:
            {{ '' | faker_name_list }}
            {{ '' | faker_name_list(count=6) }}
            {{ '' | faker_name_list(locale='en') }}
            {{ '' | faker_name_list(seed=42) }}
            {{ '' | faker_name_list(count=6, locale='en', seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return [fake.name() for _ in range(int(count))]

    def faker_company_list(self, text='', count=3, locale='es', seed=None):
        """
        Generate a list of random companies with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            count: Number of companies in the list
            locale: 'es' or 'en'
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated companies list.

        Usage:
            {{ '' | faker_company_list }}
            {{ '' | faker_company_list(count=6) }}
            {{ '' | faker_company_list(locale='en') }}
            {{ '' | faker_company_list(seed=42) }}
            {{ '' | faker_company_list(count=6, locale='en', seed=42) }}
        
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        fake = fake_es if locale == 'es' else fake_en
        return [fake.company() for _ in range(int(count))]

    def faker_dni(self, text='', seed=None):
        """
        Generate a random Spanish DNI (National ID) with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated Spanish DNI.

        Usage:
            {{ '' | faker_dni }}
            {{ '' | faker_dni(seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        number = random.randint(10000000, 99999999)
        letter = letters[number % 23]
        return f"{number}{letter}"

    def faker_cif(self, text='', seed=None):
        """
        Generate a random Spanish CIF (Company Tax ID) with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated Spanish CIF.

        Usage:
            {{ '' | faker_cif }}
            {{ '' | faker_cif(seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        
        initial_letter = random.choice('ABCDEFGHJNPQRSUVW')
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        final_letter = random.choice('ABCDEFGHIJ')
        return f"{initial_letter}{numbers}{final_letter}"

    def faker_iban(self, text='', seed=None):
        """
        Generate a random Spanish IBAN with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated Spanish IBAN.

        Usage:
            {{ '' | faker_iban }}
            {{ '' | faker_iban(seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.iban()

    def faker_lorem_text(self, text='', num_words=50, seed=None):
        """
        Generate Lorem Ipsum text with optional seed
        
        Args:
            text: Dummy parameter (for pipe compatibility)
            num_words: Number of words
            seed: Random seed for reproducibility (optional)

        Returns:
            str: Randomly generated text.

        Usage:
            {{ '' | faker_lorem_text }}
            {{ '' | faker_lorem_text(num_words=15) }}
            {{ '' | faker_lorem_text(seed=42) }}
            {{ '' | faker_lorem_text(num_words=15, seed=42) }}
        """
        if seed is not None:
            Faker.seed(int(seed))
            random.seed(int(seed))
        return fake_es.text(max_nb_chars=int(num_words) * 5)
