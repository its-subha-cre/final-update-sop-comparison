import sys
import os
import shutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j import GraphDatabase
from config import config_instance
from graph.writer import GraphWriter

def test_deletion_pipeline():
    print("=== STARTING DELETION VERIFICATION ===")
    
    # 1. Setup mock files on disk
    global_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "global")
    local_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "local")
    os.makedirs(global_dir, exist_ok=True)
    os.makedirs(local_dir, exist_ok=True)
    
    mock_global_filename = "mock_global_for_delete_test.docx"
    mock_local_filename = "mock_local_for_delete_test.docx"
    
    g_path = os.path.join(global_dir, mock_global_filename)
    l_path = os.path.join(local_dir, mock_local_filename)
    
    with open(g_path, "w") as f:
        f.write("Mock Global SOP content")
    with open(l_path, "w") as f:
        f.write("Mock Local SOP content")
        
    print(f"Created mock global file: {g_path}")
    print(f"Created mock local file: {l_path}")
    
    # 2. Setup mock graph nodes in Neo4j (if online)
    driver = None
    neo4j_online = True
    try:
        driver = GraphDatabase.driver(
            config_instance.NEO4J_URI,
            auth=(config_instance.NEO4J_USER, config_instance.NEO4J_PASSWORD)
        )
        driver.verify_connectivity()
    except Exception:
        neo4j_online = False
        print("Neo4j is offline, skipping graph-level checks.")
    
    if neo4j_online:
        writer = GraphWriter()
        
        # Write global nodes
        global_nodes = [
            {"label": "SOP", "id": "global_sop", "properties": {"name": "Mock Global SOP", "type": "Global"}},
            {"label": "Section", "id": "global_sec_1", "properties": {"title": "Global Section 1"}},
            {"label": "Clause", "id": "global_cls_1", "properties": {"text": "Global Clause 1"}}
        ]
        global_rels = [
            {"source_id": "global_sop", "target_id": "global_sec_1", "type": "HAS_SECTION", "properties": {}},
            {"source_id": "global_sec_1", "target_id": "global_cls_1", "type": "HAS_CLAUSE", "properties": {}}
        ]
        
        # Write local nodes + a custom entity linked (e.g. PPE: Nitrile Gloves)
        local_nodes = [
            {"label": "SOP", "id": l_path, "properties": {"name": mock_local_filename, "type": "Local"}},
            {"label": "Section", "id": "local_sec_1", "properties": {"title": "Local Section 1"}},
            {"label": "Clause", "id": "local_cls_1", "properties": {"text": "Local Clause 1"}},
            {"label": "PPE", "id": "nitrile_gloves_mock", "properties": {"name": "Nitrile Gloves"}}
        ]
        local_rels = [
            {"source_id": l_path, "target_id": "local_sec_1", "type": "HAS_SECTION", "properties": {}},
            {"source_id": "local_sec_1", "target_id": "local_cls_1", "type": "HAS_CLAUSE", "properties": {}},
            {"source_id": "local_cls_1", "target_id": "nitrile_gloves_mock", "type": "REQUIRES", "properties": {}},
            {"source_id": "local_cls_1", "target_id": "global_cls_1", "type": "COMPLIES_WITH", "properties": {}}
        ]
        
        print("Writing mock nodes and relationships to Neo4j...")
        writer.write_agent_output(global_nodes, global_rels)
        writer.write_agent_output(local_nodes, local_rels)
        
        # Verify nodes exist
        with driver.session() as session:
            res = session.run("MATCH (n:SOP {id: $id}) RETURN count(n) as c", id=l_path)
            assert list(res)[0]["c"] == 1, "Local SOP node not written successfully!"
            res = session.run("MATCH (n:PPE {id: 'nitrile_gloves_mock'}) RETURN count(n) as c")
            assert list(res)[0]["c"] == 1, "Mock PPE node not written successfully!"
            print("Mock graph verified successfully in Neo4j.")
            
    # 3. Simulate deletion request to the API deletion service logic
    print("Simulating deletion service trigger for the mock local SOP...")
    from app import app
    client = app.test_client()
    
    payload = {
        "sops": [
            {"filename": mock_local_filename, "type": "local"}
        ]
    }
    
    response = client.post("/api/sops/delete", json=payload)
    print("API Response:", response.json)
    assert response.status_code == 200
    if neo4j_online:
        assert response.json["success"] is True
    assert response.json["deleted_count"] == 1
    
    # 4. Assertions post-deletion
    # - Assert file is deleted on disk
    assert not os.path.exists(l_path), "Local file was not deleted from disk!"
    print("Assertion passed: Local SOP file was successfully deleted from disk.")
    
    if neo4j_online and driver:
        # - Assert local SOP, sections, and clauses are deleted in Neo4j
        with driver.session() as session:
            res = session.run("MATCH (sop:SOP) WHERE sop.id = $id RETURN count(sop) as c", id=l_path)
            assert list(res)[0]["c"] == 0, "SOP node still exists in Neo4j!"
            
            res = session.run("MATCH (sec:Section {id: 'local_sec_1'}) RETURN count(sec) as c")
            assert list(res)[0]["c"] == 0, "Section node still exists in Neo4j!"
            
            res = session.run("MATCH (c:Clause {id: 'local_cls_1'}) RETURN count(c) as c")
            assert list(res)[0]["c"] == 0, "Clause node still exists in Neo4j!"
            
            # - Assert orphaned dynamic entities (like Nitrile Gloves) are cleaned up
            res = session.run("MATCH (n:PPE {id: 'nitrile_gloves_mock'}) RETURN count(n) as c")
            assert list(res)[0]["c"] == 0, "Orphaned PPE node was not cleaned up!"
            
            # - Assert global node still remains untouched
            res = session.run("MATCH (n:SOP {id: 'global_sop'}) RETURN count(n) as c")
            assert list(res)[0]["c"] == 1, "Global SOP node was accidentally deleted!"
            
        print("Assertion passed: SOP subgraph and orphaned nodes successfully deleted.")
    
    # Cleanup global mock files and db nodes
    if os.path.exists(g_path):
        os.remove(g_path)
    if neo4j_online and driver:
        with driver.session() as session:
            session.run("MATCH (sop:SOP {id: 'global_sop'}) OPTIONAL MATCH (sop)-[:HAS_SECTION]->(sec:Section) OPTIONAL MATCH (sec)-[:HAS_CLAUSE]->(c:Clause) DETACH DELETE sop, sec, c")
            session.run("MATCH (n) WHERE NOT n:SOP AND NOT n:Section AND NOT n:Clause AND NOT (n)--() DELETE n")
            
    if driver:
        driver.close()
    print("=== DELETION VERIFICATION COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_deletion_pipeline()
