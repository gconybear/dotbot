import streamlit as st 

import boto3
from boto3.dynamodb.conditions import Key 
import uuid   
from decimal import Decimal

def format_floats(d):
    for k, v in d.items():
        if isinstance(v, float):
            d[k] = Decimal(str(v))
        elif isinstance(v, dict):
            d[k] = format_floats(v)
        elif isinstance(v, list):
            d[k] = [format_floats(item) if isinstance(item, dict) else item for item in v]
    return d


class miniDDB:

    def __init__(self, 
                 table_name: str, 
                 access_key_id=st.secrets['MASTER_ACCESS_KEY'], 
                 secret_access_key=st.secrets['MASTER_SECRET'], 
                 region_name='us-west-1'): 
        
        self.dynamodb_resource = boto3.resource('dynamodb',
                                                aws_access_key_id=access_key_id,
                                                aws_secret_access_key=secret_access_key,
                                                region_name=region_name) 
        self.dynamodb_client = boto3.client('dynamodb',
                                            aws_access_key_id=access_key_id,
                                            aws_secret_access_key=secret_access_key,
                                            region_name=region_name)
        self.table = self.dynamodb_resource.Table(table_name) 
        
    def get_item_by_id(self, item_id):
        """
        Retrieves an item from the table using the primary key.

        :param item_id: The ID of the item to retrieve.
        :return: The item if found, or None otherwise.
        """
        try:
            response = self.table.get_item(Key={'id': item_id})
            return response.get('Item')
        except self.dynamodb_resource.meta.client.exceptions.ResourceNotFoundException:
            # Handle the exception if the table does not exist
            print(f"Table not found: {self.table.table_name}")
            return None
        except self.dynamodb_resource.meta.client.exceptions.ClientError as e:
            # Handle other possible exceptions
            print(f"Failed to get item: {e.response['Error']['Message']}")
            return None
    
    def add_item(self, item, auto_id=True):
        """
        Adds an item to the table.

        :param item: Dictionary containing the item to add.
        :return: The ID of the created item.
        """ 
        if auto_id:
            item['id'] = str(uuid.uuid4()) 
        
        assert 'id' in item, 'Item must have an ID' 

        self.table.put_item(Item=item)
        return item['id'] 
        
    def update_item(self, _id, update):
        """
        Updates an item in the table with the given ID.

        :param _id: The ID of the item to update.
        :param update: Dictionary containing the update expressions.
        :return: The response from the DynamoDB update_item call.
        """
        update_expression = "SET " + ", ".join(f"{k}=:{k}" for k in update.keys())
        expression_attribute_values = {f":{k}": v for k, v in update.items()}

        response = self.table.update_item(
            Key={'id': _id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW"
        )
        return response 
        
    def query_by_index(self, query_params):
        """
        Queries the table using a specified index.

        :param query_params: Dictionary with 'index', 'field', and 'value' as keys.
        :return: List of items matching the query parameters.
        """
        if not all(k in query_params for k in ('index', 'field', 'value')):
            raise ValueError("Query parameters must include 'index', 'field', and 'value'.")

        index_name = query_params['index']
        query_field = query_params['field']
        query_value = query_params['value']
        
        response = self.table.query(
            IndexName=index_name,
            KeyConditionExpression=Key(query_field).eq(query_value)
        )
        
        return response['Items']

    def delete_item(self, _id):
        """
        Deletes an item from the table with the given ID.

        :param _id: The ID of the item to delete.
        :return: The response from the DynamoDB delete_item call.
        """
        response = self.table.delete_item(
            Key={'id': _id}
        )
        return response 