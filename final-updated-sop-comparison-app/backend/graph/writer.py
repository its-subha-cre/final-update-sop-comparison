from neo4j import GraphDatabase
from config import config_instance

class GraphWriter:
    """Deterministic writer to execute parameterized Cypher writes from Agent JSON definitions."""
    
    def __init__(self):
        self.uri = config_instance.NEO4J_URI
        self.user = config_instance.NEO4J_USER
        self.password = config_instance.NEO4J_PASSWORD
        self._driver = None

    def connect(self):
        if not self._driver:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def write_agent_output(self, nodes: list, relationships: list):
        """
        Takes a list of nodes and relationships from LLM agents and writes them to Neo4j.
        Guarantees deterministic execution via parameterized Cypher statements.
        """
        self.connect()
        with self._driver.session() as session:
            session.execute_write(self._write_nodes_tx, nodes)
            session.execute_write(self._write_relationships_tx, relationships)
        return {"success": True, "nodes_written": len(nodes), "edges_written": len(relationships)}

    @staticmethod
    def _sanitize_properties(properties: dict) -> dict:
        """Ensures all property values are Neo4j-compatible primitives or lists of primitives."""
        import json
        sanitized = {}
        for k, v in properties.items():
            if isinstance(v, (dict, list, tuple)):
                if isinstance(v, (list, tuple)):
                    if all(isinstance(item, (str, int, float, bool)) for item in v):
                        sanitized[k] = list(v)
                    else:
                        sanitized[k] = json.dumps(v)
                else:
                    sanitized[k] = json.dumps(v)
            elif isinstance(v, (str, int, float, bool)) or v is None:
                sanitized[k] = v
            else:
                sanitized[k] = str(v)
        return sanitized

    @staticmethod
    def _write_nodes_tx(tx, nodes):
        """Writes/updates nodes using dynamic sanitized labels from LLM decisions."""
        import re
        for node in nodes:
            label = node.get("label", "Node")
            node_id = node.get("id")
            properties = node.get("properties", {})
            
            clean_properties = GraphWriter._sanitize_properties(properties)
            
            # Sanitize label to prevent injection while allowing arbitrary naming
            clean_label = re.sub(r'[^a-zA-Z0-9_]', '', label)
            if not clean_label:
                clean_label = "Node"
                
            query = f"""
            MERGE (n:{clean_label} {{id: $node_id}})
            SET n += $properties
            RETURN n.id
            """
            tx.run(query, node_id=node_id, properties=clean_properties)

    @staticmethod
    def _write_relationships_tx(tx, relationships):
        """Wires arbitrary relationships between nodes dynamically."""
        import re
        for rel in relationships:
            source_id = rel.get("source_id")
            target_id = rel.get("target_id")
            rel_type = rel.get("type", "RELATED_TO")
            properties = rel.get("properties", {})
            
            clean_properties = GraphWriter._sanitize_properties(properties)
            
            # Sanitize type to prevent injection while allowing arbitrary naming
            clean_type = re.sub(r'[^a-zA-Z0-9_]', '', rel_type)
            if not clean_type:
                clean_type = "RELATED_TO"
                
            query = f"""
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            MERGE (source)-[r:{clean_type}]->(target)
            SET r += $properties
            RETURN type(r)
            """
            tx.run(query, source_id=source_id, target_id=target_id, properties=clean_properties)