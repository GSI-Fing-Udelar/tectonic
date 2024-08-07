# Caldera
In order to upload resources to Caldera you must provide a `caldera` directory with the following structure:

```
caldera
├── abilities
│   ├── <tactic_1>
│   │   └── <ability_id>.yml
│   └── <tactic_N>
│       └── <ability_id>.yml
├── adversaries
│   └── <adversarie_id.yml
├── operations
│   └── <operation_name>.json
└── sources
    └── <source_id>.yml

```
## Abilities
An ability is a specific Mitre ATT&CK tactic/technique implementation which can be executed on running agents. To export abilities just copy the directory `CALDERA_INSTALLATION_PATH/data/abilities/`. Abilities are defined in YAML files whose name corresponds to the unique identifier of the ability. The skills are distributed in a directory structure, where each directory corresponds to a tactic of the Miter ATT&CK framework

## Adversaries
Adversary profiles are groups of abilities, representing the tactics, techniques, and procedures (TTPs) available to a threat actor. To export adversaires just copy the directory `CALDERA_INSTALLATION_PATH/data/adversaries/`. Adversaries are defined in YAML files whose name corresponds to the unique identifier of the adversary.

## Operations
Operations run abilities on agent groups. To define an operation, a JSON must be generated. The easiest way to get this JSON is to define the operation in Caldera, search for the HTTP request sent when doing so (for example using the browser developer tools) and copy the JSON content of the request in a JSON file. Below is an example JSON:

```
{
    "name":"Operation Name",
    "autonomous":1,
    "use_learning_parsers":true,
    "auto_close":false,
    "jitter":"1/10",
    "state":"paused",
    "visibility":51,
    "obfuscator":"plain-text",
    "source":{"id":"bc8b5680-5968-4167-bc2a-87abf4cad4d7"},
    "planner":{"id":"aaa7c857-37a0-4c4a-85f7-4e9f7f30e31a"},
    "adversary":{"adversary_id":"2a9e9c0c-724a-43dd-b8c4-4e61c801af63"},
    "group":"red"
}

```

## Sources
A fact is an identifiable piece of information about a given computer. Facts can be used to perform variable assignment within abilities. A fact source is a collection of facts that you have grouped together. A fact source can be applied to an operation when you start it, which gives the operation facts to fill in variables with. To export facts sources just copy the directory `CALDERA_INSTALLATION_PATH/data/sources/`. Facts sources are defined in YAML files whose name corresponds to the unique identifier of the fact source.


