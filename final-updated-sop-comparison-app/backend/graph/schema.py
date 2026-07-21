from neo4j import GraphDatabase
from config import config_instance

class Neo4jSchema:
    """Orchestrates creation of Neo4j uniqueness constraints and schema indices."""
    
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

    def setup_constraints(self):
        """Creates unique constraints to prevent duplication during writes."""
        self.connect()
        queries = [
            "CREATE CONSTRAINT sop_id_unique IF NOT EXISTS FOR (s:SOP) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT section_id_unique IF NOT EXISTS FOR (sec:Section) REQUIRE sec.id IS UNIQUE",
            "CREATE CONSTRAINT subsection_id_unique IF NOT EXISTS FOR (sub:Subsection) REQUIRE sub.id IS UNIQUE",
            "CREATE CONSTRAINT clause_id_unique IF NOT EXISTS FOR (c:Clause) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT control_id_unique IF NOT EXISTS FOR (con:Control) REQUIRE con.id IS UNIQUE",
            "CREATE CONSTRAINT context_id_unique IF NOT EXISTS FOR (ctx:ContextNode) REQUIRE ctx.id IS UNIQUE",
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (ent:Entity) REQUIRE ent.id IS UNIQUE",
            "CREATE CONSTRAINT equipment_id_unique IF NOT EXISTS FOR (eq:Equipment) REQUIRE eq.id IS UNIQUE",
            "CREATE CONSTRAINT risk_id_unique IF NOT EXISTS FOR (rk:Risk) REQUIRE rk.id IS UNIQUE",
            "CREATE CONSTRAINT regulation_id_unique IF NOT EXISTS FOR (reg:Regulation) REQUIRE reg.id IS UNIQUE",
            "CREATE CONSTRAINT recommendation_id_unique IF NOT EXISTS FOR (rec:Recommendation) REQUIRE rec.id IS UNIQUE",
            "CREATE CONSTRAINT business_process_id_unique IF NOT EXISTS FOR (bp:BusinessProcess) REQUIRE bp.id IS UNIQUE",
            "CREATE CONSTRAINT department_id_unique IF NOT EXISTS FOR (dept:Department) REQUIRE dept.id IS UNIQUE",
            "CREATE CONSTRAINT role_id_unique IF NOT EXISTS FOR (rl:Role) REQUIRE rl.id IS UNIQUE"
        ]
        
        with self._driver.session() as session:
            for q in queries:
                try:
                    session.run(q)
                    print(f"Applied Cypher: {q}")
                except Exception as e:
                    print(f"Error applying Cypher: {q}. Exception: {e}")

    def create_vector_indices(self):
        """Creates vector index on Clause text embeddings for vector similarity lookup."""
        self.connect()
        # Neo4j 5.x syntax for vector search index creation
        query = """
        CREATE VECTOR INDEX clause_embeddings_idx IF NOT EXISTS
        FOR (c:Clause)
        ON (c.embedding)
        OPTIONS {indexConfig: {
          `vector.dimensions`: 1536,
          `vector.similarity_function`: 'cosine'
        }}
        """
        with self._driver.session() as session:
            try:
                session.run(query)
                print(f"Applied Cypher: Vector Index created.")
            except Exception as e:
                print(f"Error creating vector index: {e}")

def run_schema_setup():
    schema = Neo4jSchema()
    try:
        schema.setup_constraints()
        schema.create_vector_indices()
    finally:
        schema.close()

if __name__ == "__main__":
    run_schema_setup()
