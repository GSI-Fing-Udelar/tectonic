# Elastic
In order to upload resources to Elasticsearch, Kibana and Fleet you must provide a `elastic` directory with the following structure:

```
elastic
├── <monitor_type>
        ├── elasticsearch
        │   ├── component_templates
        |   |   └── <component_template_name>.json
        │   ├── ilm_policies
        |   |   └── <ilm_policy_name>.json
        │   ├── index_templates
        |   |   └── <index_template_name>.json
        │   └── ingest_pipelines
        │       └── <ingest_pipeline_name>.json
        ├── fleet
        │   ├── agent_policies
        │   │   └── <agent_policy_name>.json
        │   └── policy_integrations
        │       └── <agent_policy_name>
        │           └── <integration_name>.json
        └── kibana
            ├── saved_objects
            │   └── export.ndjson
            └── security_rules
                └── rules_export.ndjson
```
where `monitor_type` is one of endpoint or network.


### Elasticsearch
Each subdirectory contains JSON files with the configuration of each Elasticsearch resource type. Files names will match the unique name of the resource once it is configured in Elasticsearch.

#### Component templates

**Component templates** are building blocks for constructing index templates. To export components templates you must follow these steps:
1. In Kibana go to *Management -> Stack Management* menu.
2. Go to *Data -> Index Management* submenu.
3. Click on *Component Templates*.
4. Click on the component template to export. Then click on the *Manage* button and then on *Edit*.
5. Go to step *5 - Review* and click on *Request*. At this point you should be seeing the HTTP request needed to create the component template.
6. Create a file in *component_templates* directory with:
    - Name: same as the componente template. Use the last part of the request URI.
    - Extension: JSON extension (.json)
    - Content: component template configuration in JSON format. Use the request body content.


#### ILM policies

**Index Lifecycle Management (ILM)** policies are used to automatically manage indices. To export IML policies you must follow these steps:
1. In Kibana go to *Management -> Stack Management* menu.
2. Go to *Data -> Index Lifecycle Policies* submenu.
3. Click on the ILM policy to export. Then click on the *Show request* button. At this point you should be seeing the HTTP request needed to create the ILM policy.
4. Create a file in *ilm_policies* directory with:
    - Name: same as the ILM policy. Use the last part of the request URI.
    - Extension: JSON extension (.json)
    - Content: ILM policy configuration in JSON format. Use the request body content.

#### Index templates

**Index templates** is a way to tell Elasticsearch how to configure an index when it is created. To export index templates you must follow these steps:
1. In Kibana go to *Management -> Stack Management* menu.
2. Go to *Data -> Index Management* submenu.
3. Click on *Index Templates*.
4. Click on the index template to export. Then click on the *Manage* button and then on *Edit*.
5. Go to step *6 - Review template* and click on *Request*. At this point you should be seeing the HTTP request needed to create the index template.
6. Create a file in *index_templates* directory with:
    - Name: same as the index template. Use the last part of the request URI.
    - Extension: JSON extension (.json)
    - Content: index template configuration in JSON format. Use the request body content.

#### Ingest pipelines
**Ingest pipelines** let you perform common transformations on your data before indexing. To export ingest pipelines you must follow these steps:
1. In Kibana go to *Management -> Stack Management* menu.
2. Go to *Ingest -> Ingest Pipelines* submenu.
3. Click on the component template to export. Then click on the *Manage* button and then on *Edit*.
4. Click on the *Show request* button. At this point you should be seeing the HTTP request needed to create the ingest pipeline.
5. Create a file in *ingest_pipelines* directory with:
    - Name: same as the ingest pipeline. Use the last part of the request URI.
    - Extension: JSON extension (.json)
    - Content: ingest pipeline configuration in JSON format. Use the request body content.

### Fleet
Each subdirectory contains JSON files with the configuration of each Fleet resource type.

#### Agent Policies
An **agent policy** is a collection of inputs and settings that defines the data to be collected by an Elastic Agent. To export agent policies you must follow these steps:
1. In Kibana go to *Management -> Fleet* menu.
2. Click on *Agent Policies* and then click on *Create agent policy*.
3. Fill out the form fields as necessary and then click on *Preview API request*. At this point you should be seeing the HTTP request needed to create the agent policy.
4. Create a file in *agent_policy* directory with:
    - Name: same as the agent policy. Use the field *name* of the request body.
    - Extension: JSON extension (.json)
    - Content: agent policy configuration in JSON format. Use the request body content.

By default, a default policy named Packetbeat or Endpoint is deployed that allows monitoring of network events or hosts events in the scenario. If you use the name Packetbeat/Endpoint for your custom policy then you must set the variable elastic_deployment.deploy_default_policy to no. Otherwise your policy will collide with the default deployed policy for Packetbeat/Endpoint and the deployment will fail.

#### Policy Integrations
**Elastic Agent integrations** provide a simple, unified way to collect data from popular apps and services, and protect systems from security threats. Integrations are added to an agent policy. To export policy integrations you must follow these steps:
1. In Kibana go to *Management -> Fleet* menu.
2. Click on *Agent Policies* and then click on an agent policy (or create a new one).
3. Click on *Add integration* and select your integration. Configure the integrations as needed. Click on *Preview API request* button. At this point you should be seeing the HTTP request needed to create the integration for the specific agent policy.
4. In *policy_integration* directory create a subdirectory with the same name as the agent policy used for the integration. Then in this subdirectory create a JSON file for the integration with:
    - Name: same as the integration. Use the field *name* of the request body.
    - Extension: JSON extension (.json)
    - Content: integration configuration in JSON format. Use the request body content.

You can configure your own integrations for the default Packetbeat/Endpoint agent policy. For this you must create the *Packetbeat* or *Endpoint* subdirectory with the necessary integrations files. If you deploy the default Packetbeat or Endpoint integration, you cannot use the name "Packetbeat" or "Endpoint" for your custom integrations.

Make sure to deploy a policy whose name matches the value configured in the packetbeat_policy_name or endpoint_policy_name options in the teconic.ini file. Otherwise, the deployment will fail.

### Kibana
Each subdirectory contains NDJSON files with the configuration of each Kibana resource type.

#### Saved Objects
**Saved objects** include dashboards, visualizations, maps, data views, Canvas workpads, and others. To export saved objects you must follow these steps:
1. In Kibana go to *Management -> Stack Management* menu.
2. Go to *Kiabana -> Saved objects* submenu.
3. Select all the saved objects you want to export (do not include rules type saved objects).
4. Click on *Export* button.
5. Select *Include related objects* option and the click on *Export*. At this point the export.ndjson file should have downloaded. Move this file to the directory *saved_objects*.

#### Security rules
**Security Rules** run periodically and search for source events, matches, sequences, or machine learning job anomaly results that meet their criteria. When a rule’s criteria are met, a detection alert is created. To export security rules you must follow these steps:
1. In Kibana go to *Security -> Rules* menu.
2. Click on *Detection rules (SIEM)*.
3. Select all the rules you want to export. Make sure that this rules are enabled so that after being imported they are also enabled by default.
4. Click on *Bulk actions* and then on *Export*. At this point the rules_export.ndjson file should have downloaded. Move this file to the directory *security_rules*. 


#### Installation of Packetbeat
When the instances monitoring type is traffic and the platform is libvirt or docker, Packetbeat must be configured on the host. In case you have any kind of network problem, you can download elastic-agent from the internet and unzip it in the directory /opt/elastic-agent-{{ elastic_agent_version }}-linux-x86_64/
