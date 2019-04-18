#(C) Copyright 2018 Hewlett Packard Enterprise Development LP

import bottle
import requests
import json
import os
import subprocess

X_BROKER_API_MAJOR_VERSION = 2
X_BROKER_API_MINOR_VERSION = 3
X_BROKER_API_VERSION_NAME = 'X-Broker-API-Version'

# UPDATE THIS FOR YOUR ECHO SERVICE DEPLOYMENT
# service endpoint templates
service_binding = "http://localhost:8090/echo/{{instance_id}}/{{binding_id}}"


#sudo pip install gunicorn
# services
service = {
    "name": "fake-service",
    "id": "8fc05a9f-897a-11e8-a687-feb140a59a66",
    "description": "fake service",
    "tags": ["no-sql", "relational"],
    "requires": ["route_forwarding"],
    "bindable": True,
    "metadata": {
      "provider": {
        "name": "The name"
      },
      "listing": {
        "imageUrl": "http://example.com/cat.gif",
        "blurb": "Add a blurb here",
        "longDescription": "A long time ago, in a galaxy far far away..."
      },
      "displayName": "The Fake Broker"
    },
    "dashboard_client": {
      "id": "398e2f8e-XXXX-XXXX-XXXX-19a71ecbcf64",
      "secret": "277cabb0-XXXX-XXXX-XXXX-7822c0a90e5d",
      "redirect_uri": "http://localhost:1234"
    },
    "plan_updateable": True,
    "plans": [{
      "name": "fake-plan-1",
      "id": "8fc05a9f-897a-11e8-a687-0242ac110008",
      "description": "Shared fake Server, 5tb persistent disk, 40 max concurrent connections",
      "free": False,
      "metadata": {
        "max_storage_tb": 5,
        "costs":[
            {
               "amount":{
                  "usd":99.0
               },
               "unit":"MONTHLY"
            },
            {
               "amount":{
                  "usd":0.99
               },
               "unit":"1GB of messages over 20GB"
            }
         ],
        "bullets": [
          "Shared fake server",
          "5 TB storage",
          "40 concurrent connections"
        ]
      },
      "schemas": {
        "service_instance": {
          "create": {
            "parameters": {
              "$schema": "http://json-schema.org/draft-04/schema#",
              "type": "object",
              "properties": {
                "billing-account": {
                  "description": "Billing account number used to charge use of shared fake server.",
                  "type": "string"
                }
              }
            }
          },
          "update": {
            "parameters": {
              "$schema": "http://json-schema.org/draft-04/schema#",
              "type": "object",
              "properties": {
                "billing-account": {
                  "description": "Billing account number used to charge use of shared fake server.",
                  "type": "string"
                }
              }
            }
          }
        },
        "service_binding": {
          "create": {
            "parameters": {
              "$schema": "http://json-schema.org/draft-04/schema#",
              "type": "object",
              "properties": {
                "billing-account": {
                  "description": "Billing account number used to charge use of shared fake server.",
                  "type": "string"
                }
              }
            }
          }
        }
      }
    }, {
      "name": "fake-plan-2",
      "id": "8fc05a9f-897a-11e8-a687-0242ac110648",
      "description": "Shared fake Server, 5tb persistent disk, 40 max concurrent connections. 100 async",
      "free": False,
      "metadata": {
        "max_storage_tb": 5,
        "costs":[
            {
               "amount":{
                  "usd":199.0
               },
               "unit":"MONTHLY"
            },
            {
               "amount":{
                  "usd":0.99
               },
               "unit":"1GB of messages over 20GB"
            }
         ],
        "bullets": [
          "40 concurrent connections"
        ]
      }
    }]
}

@bottle.error(401)
@bottle.error(409)
def error(error):
    bottle.response.content_type = 'application/json'
    return '{"error": "%s"}' % error.body

def authenticate(username, password):
    return True

@bottle.route('/v2/service_instances/<instance_id>/last_operation', method='GET')
@bottle.auth_basic(authenticate)
def last_operation(instance_id):
    """
    Return the catalog of services handled
    by this broker

    GET /v2/service_instances/<instance_id>/last_operation

    HEADER:
        X-Broker-API-Version: <version>

    return:
        JSON document with details about the
        services offered through this broker
    """
    api_version = bottle.request.headers.get('X-Broker-API-Version')
    if (not api_version or not (api_version_is_valid(api_version))):
        bottle.abort(
            409,
            "Missing or incompatible %s. Expecting version %.0f.%.0f or later" % (
                X_BROKER_API_VERSION_NAME,
                X_BROKER_API_MAJOR_VERSION,
                X_BROKER_API_MINOR_VERSION))
    return {"state": "succeeded"}

@bottle.route('/v2/catalog', method='GET')
@bottle.auth_basic(authenticate)
def catalog():
    """
    Return the catalog of services handled
    by this broker

    GET /v2/catalog:

    HEADER:
        X-Broker-API-Version: <version>

    return:
      JSON document with details about the
      services offered through this broker

      Using OSB Spec of Get Catalog:
      https://github.com/openservicebrokerapi/servicebroker/blob/v2.13/spec.md
    """
    api_version = bottle.request.headers.get('X-Broker-API-Version')
    if (not api_version or not (api_version_is_valid(api_version))):
        bottle.abort(
            409,
            "Missing or incompatible %s. Expecting version %.0f.%.0f or later" % (
                X_BROKER_API_VERSION_NAME,
                X_BROKER_API_MAJOR_VERSION,
                X_BROKER_API_MINOR_VERSION))
    return {"services": [service]}

def api_version_is_valid(api_version):
    version_data = api_version.split('.')
    result = True
    if (float(version_data[0]) < X_BROKER_API_MAJOR_VERSION
        or (float(version_data[0]) == X_BROKER_API_MAJOR_VERSION
            and float(version_data[1]) < X_BROKER_API_MINOR_VERSION)):
                result = False
    return result


@bottle.route('/v2/service_instances/<instance_id>', method='PUT')
@bottle.auth_basic(authenticate)
def provision(instance_id):
    """
    Provision an instance of this service
    for the given org and space

    PUT /v2/service_instances/<instance_id>:
        <instance_id> is provided by the Cloud
          Controller and will be used for future
          requests to bind, unbind and deprovision

    BODY:
        {
          "service_id":        "<service-guid>",
          "plan_id":           "<plan-guid>",
          "organization_guid": "<org-guid>",
          "space_guid":        "<space-guid>"
        }

    return:
        JSON document with details about the
        services offered through this broker
    """
    if bottle.request.content_type != 'application/json':
        bottle.abort(415, 'Unsupported Content-Type: expecting application/json')
    # get the JSON document in the BODY
    provision_details = bottle.request.json
    bottle.response.status = 201
    dashboard_url = "www.google.com"
    #return {}
    return {"dashboard_url": dashboard_url}

@bottle.route('/v2/service_instances/<instance_id>', method='DELETE')
@bottle.auth_basic(authenticate)
def deprovision(instance_id):
    """
    Deprovision an existing instance of this service

    DELETE /v2/service_instances/<instance_id>:
        <instance_id> is the Cloud Controller provided
          value used to provision the instance

   return:
        As of API 2.3, an empty JSON document
        is expected
    """
    # send response
    return {}

@bottle.route('/v2/service_instances/<instance_id>/service_bindings/<binding_id>', method='PUT')
@bottle.auth_basic(authenticate)
def bind(instance_id, binding_id):
    """
    Bind an existing instance with the
    for the given org and space

    PUT /v2/service_instances/<instance_id>/service_bindings/<binding_id>:
        <instance_id> is the Cloud Controller provided
          value used to provision the instance
        <binding_id> is provided by the Cloud Controller
          and will be used for future unbind requests

    BODY:
        {
          "plan_id":           "<plan-guid>",
          "service_id":        "<service-guid>",
          "app_guid":          "<app-guid>"
        }

    return:
        JSON document with credentails and access details
        for the service based on this binding
        http://docs.cloudfoundry.org/services/binding-credentials.html
    """
    if bottle.request.content_type != 'application/json':
        bottle.abort(415, 'Unsupported Content-Type: expecting application/json')
    # get the JSON document in the BODY
    binding_details = bottle.request.json
    print(binding_details)
    bottle.response.status = 201
    return {"credentials": {"uri": bottle.template(service_binding, instance_id=instance_id, binding_id=binding_id), "username": "mysqluser"}}

@bottle.route('/v2/service_instances/<instance_id>/service_bindings/<binding_id>', method='DELETE')
@bottle.auth_basic(authenticate)
def unbind(instance_id, binding_id):
    """
    Unbind an existing instance associated
    with the binding_id provided

    DELETE /v2/service_instances/<instance_id>/service_bindings/<binding_id>:
        <instance_id> is the Cloud Controller provided
          value used to provision the instance
        <binding_id> is the Cloud Controller provided
          value used to bind the instance

    return:
        As of API 2.3, an empty JSON document
        is expected
    """
    return {}

if __name__ == '__main__':
    port = int(os.getenv('PORT', '7099'))
    bottle.run(host='0.0.0.0', port=port, debug=True, reloader=False, server='gunicorn')
    #bottle.run(host='172.18.203.43', port=port, debug=True, reloader=False, certfile='/home/ubuntu/.minikube/ca.crt', keyfile='/home/ubuntu/.minikube/ca.key', server='gunicorn')
