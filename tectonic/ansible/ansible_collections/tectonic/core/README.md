# Ansible Collection - tectonic.core

## Description
Collection for common Tectonic cyber range functions.

## Filters

This collection includes the following filters for the synthetic generation of data.

### faker_name
Generate a random person name.

**Parameters:**
- text (string, optional): Dummy parameter for Jinja2 pipe compatibility. Default: ''
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed for reproducibility. Default: None

**Returns:**
- string – Randomly generated name.

**Usage:**
```yaml
{{ '' | faker_name }}  
{{ '' | faker_name(locale='en') }}  
{{ '' | faker_name(seed=42) }}  
{{ '' | faker_name(locale='en', seed=42) }}  
```

### faker_company
Generate a random company name.

**Parameters:**
- text (string, optional): Dummy parameter for Jinja2 pipe compatibility. Default: ''
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed for reproducibility. Default: None

**Returns:**
-  string – Randomly generated company name.

**Usage:**
```yaml
{{ '' | faker_company }}  
{{ '' | faker_company(locale='en') }}  
{{ '' | faker_company(seed=42) }}  
{{ '' | faker_company(locale='en', seed=42) }}  
```

### faker_email
Generate a random email address.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Randomly generated email.

**Usage:**
```yaml
{{ '' | faker_email }}  
{{ '' | faker_email(seed=42) }}  
```

### faker_phone
Generate a random phone number.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Randomly generated phone number.

**Usage:**
```yaml
{{ '' | faker_phone }}  
{{ '' | faker_phone(locale='en', seed=42) }}  
```

### faker_address
Generate a random address.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Randomly generated address.

**Usage:**
```yaml
{{ '' | faker_address }}  
{{ '' | faker_address(locale='en', seed=42) }}  
```

### faker_city
Generate a random city.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Randomly generated city.

**Usage:**
```yaml
{{ '' | faker_city }}  
{{ '' | faker_city(locale='en', seed=42) }}  
```

### faker_country
Generate a random country.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Randomly generated country.

**Usage:**
```yaml
{{ '' | faker_country }}  
{{ '' | faker_country(locale='en', seed=42) }}  
```

### faker_paragraph
Generate a random paragraph.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- num_sentences (int, optional): Number of sentences. Default: 5
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random paragraph.

**Usage:**
```yaml
{{ '' | faker_paragraph }}  
{{ '' | faker_paragraph(num_sentences=10) }}  
{{ '' | faker_paragraph(locale='en', seed=42) }}  
```

### faker_sentence
Generate a random sentence.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random sentence.

**Usage:**
```yaml
{{ '' | faker_sentence }}  
{{ '' | faker_sentence(locale='en', seed=42) }}  
```

### faker_date
Generate a random date (YYYY-MM-DD).

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random date.

**Usage:**
```yaml
{{ '' | faker_date }}  
{{ '' | faker_date(seed=42) }}  
```

### faker_url
Generate a random URL.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random URL.

**Usage:**
```yaml
{{ '' | faker_url }}  
{{ '' | faker_url(seed=42) }}  
```

### faker_ipv4
Generate a random IPv4 address.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random IPv4.

**Usage:**
```yaml
{{ '' | faker_ipv4 }}  
{{ '' | faker_ipv4(seed=42) }}  
```

### faker_mac
Generate a random MAC address.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random MAC address.

**Usage:**
```
{{ '' | faker_mac }}  
{{ '' | faker_mac(seed=42) }}  
```

### faker_user_agent
Generate a random user agent string.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random user agent.

**Usage:**
```yaml
{{ '' | faker_user_agent }}  
{{ '' | faker_user_agent(seed=42) }}  
```

### faker_job
Generate a random job/profession.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random job/profession.

**Usage:**
```yaml
{{ '' | faker_job }}  
{{ '' | faker_job(locale='en', seed=42) }}  
```

### faker_color
Generate a random color name.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random color.

**Usage:**
```yaml
{{ '' | faker_color }}  
{{ '' | faker_color(seed=42) }}  
```

### faker_number
Generate a random number in a range.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- minimum (int, optional): Minimum number. Default: 1
- maximum (int, optional): Maximum number. Default: 1000
- seed (int, optional): Random seed. Default: None

**Returns:**
 int – Random number.

**Usage:**
```yaml
{{ '' | faker_number }}  
{{ '' | faker_number(minimum=10, maximum=50, seed=42) }}  
```

### faker_name_list
Generate a list of random names.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- count (int, optional): Number of names. Default: 5
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed. Default: None

**Returns:**
 list of strings – Random names.

**Usage:**
```yaml
{{ '' | faker_name_list }}  
{{ '' | faker_name_list(count=6, locale='en', seed=42) }}  
```

### faker_company_list
Generate a list of random companies.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- count (int, optional): Number of companies. Default: 3
- locale (string, optional): 'es' or 'en'. Default: 'es'
- seed (int, optional): Random seed. Default: None

**Returns:**
 list of strings – Random companies.

**Usage:**
```yaml
{{ '' | faker_company_list }}  
{{ '' | faker_company_list(count=6, locale='en', seed=42) }}  
```

### faker_dni
Generate a random Spanish DNI.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random DNI.

**Usage:**
```yaml
{{ '' | faker_dni }}  
{{ '' | faker_dni(seed=42) }}  
```

### faker_cif
Generate a random Spanish CIF.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random CIF.

**Usage:**
```yaml
{{ '' | faker_cif }}  
{{ '' | faker_cif(seed=42) }}  
````

### faker_iban
Generate a random Spanish IBAN.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random IBAN.

**Usage:**
```yaml
{{ '' | faker_iban }}  
{{ '' | faker_iban(seed=42) }}  
```

### faker_lorem_text
Generate Lorem Ipsum text.

**Parameters:**
- text (string, optional): Dummy parameter. Default: ''
- num_words (int, optional): Number of words. Default: 50
- seed (int, optional): Random seed. Default: None

**Returns:**
-  string – Random text.

**Usage:**
```yaml
{{ '' | faker_lorem_text }}  
{{ '' | faker_lorem_text(num_words=15, seed=42) }}  
```
## Roles

This collection includes the following roles:

- **install_system_packages**: Install Linux system packages. 
- **install_python_libraries**: Install Python libraries using pip.

Each role has its own README with detailed usage instructions and variables.

**Usage:**
```yaml
- hosts: all
  become: yes
  roles:
    - role: tectonic.core.install_system_packages
      vars:
        packages_to_install:
          - python3
          - python3-pip
    - role: tectonic.core.install_python_libraries
      vars:
        libraries_to_install:
          - request
        python_executable: python3
        pip_executable: pip3
```