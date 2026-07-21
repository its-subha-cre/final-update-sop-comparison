import time
from typing import TypedDict, List, Dict, Any
from agents.ingestion import IngestionAgent
from agents.normalization import SectionNormalizationAgent
from agents.relationship_inference import RelationshipInferenceAgent
from agents.comparison import ComparisonAgent
from agents.validity import ValidityAssessmentAgent
from agents.report import ReportOrchestrationAgent
from services.chunker import ChunkerService
from services.scoring import ScoringService
from graph.writer import GraphWriter
from agents.llm_chunker import LLMChunkerAgent
from agents.translation import TranslationAgent

class AgentState(TypedDict):
    global_sop_path: str
    local_sop_paths: List[str]
    current_file: str
    stage: str
    raw_texts: Dict[str, str]
    original_raw_texts: Dict[str, str]
    translation_metadata: Dict[str, Any]
    chunks: Dict[str, Any]
    inference_results: Dict[str, Any]
    comparison_results: List[Any]
    validity_results: List[Any]
    report: Dict[str, Any]
    errors: List[str]
    status: str
    progress: int

class PipelineOrchestrator:
    """Orchestrates the multi-agent comparison flow with checkpointing and error retries."""

    def __init__(self):
        self.ingestion = IngestionAgent()
        self.normalization = SectionNormalizationAgent()
        self.inference = RelationshipInferenceAgent()
        self.comparison = ComparisonAgent()
        self.validity = ValidityAssessmentAgent()
        self.report_agent = ReportOrchestrationAgent()
        self.writer = GraphWriter()
        self.llm_chunker = LLMChunkerAgent()
        self.translation_agent = TranslationAgent()

    def run_pipeline(self, global_path: str, local_paths: List[str], 
                     site_context: str = "", equipment_context: str = "", 
                     regulatory_context: str = "", callback = None) -> dict:
        """Sequential execution runner with checkpoint states for robust local task execution."""
        state: AgentState = {
            "global_sop_path": global_path,
            "local_sop_paths": local_paths,
            "current_file": "",
            "stage": "queued",
            "raw_texts": {},
            "original_raw_texts": {},
            "translation_metadata": {},
            "chunks": {},
            "inference_results": {},
            "comparison_results": [],
            "validity_results": [],
            "report": {},
            "errors": [],
            "status": "in_progress",
            "progress": 0
        }

        # Step 1: Ingestion
        try:
            state["stage"] = "parsing"
            state["progress"] = 20
            if callback: callback(state)
            state["current_file"] = global_path
            state["raw_texts"]["global"] = self.ingestion.parse_file(global_path)["raw_text"]
            
            for path in local_paths:
                state["current_file"] = path
                state["raw_texts"][path] = self.ingestion.parse_file(path)["raw_text"]
        except Exception as e:
            state["status"] = "failed"
            state["errors"].append(f"Ingestion failed: {str(e)}")
            if callback: callback(state)
            return state

        # Step 1.5: Language Detection, Translation & Quality Validation
        try:
            state["stage"] = "translating"
            state["progress"] = 30
            if callback: callback(state)
            trans_meta = self.translation_agent.process_raw_texts(
                raw_texts=state["raw_texts"], 
                original_raw_texts=state["original_raw_texts"]
            )
            state["translation_metadata"] = trans_meta
        except Exception as te:
            state["errors"].append(f"Translation Agent skipped (details: {te}). Proceeding with extracted raw text.")

        # Step 2: Chunking (LLM-driven partition)
        try:
            state["stage"] = "chunked"
            state["progress"] = 40
            if callback: callback(state)
            llm_chunk_working = True
            
            try:
                # 1. Run LLM Chunking Agent for Global SOP
                global_result = self.llm_chunker.chunk_document_with_llm(
                    doc_title="Global SOP", 
                    raw_text=state["raw_texts"]["global"]
                )
                
                # Format to section-clause structure for compatibility
                sections = []
                current_sec = None
                for chunk in global_result.chunks:
                    if chunk.label.lower() in ["section", "header", "heading"]:
                        current_sec = {
                            "id": chunk.id,
                            "title": chunk.content,
                            "clauses": []
                        }
                        sections.append(current_sec)
                    else:
                        if not current_sec:
                            current_sec = {
                                "id": "sec-default",
                                "title": "General Requirements",
                                "clauses": []
                            }
                            sections.append(current_sec)
                        current_sec["clauses"].append({
                            "id": chunk.id,
                            "number": chunk.properties.get("number", "Generic"),
                            "text": chunk.content,
                            "label": chunk.label
                        })
                state["chunks"]["global"] = {"sop_id": "global_sop", "sections": sections}
                
                # 2. Run LLM Chunking Agent for each Local SOP
                for path in local_paths:
                    local_result = self.llm_chunker.chunk_document_with_llm(
                        doc_title=path, 
                        raw_text=state["raw_texts"][path]
                    )
                    local_sections = []
                    current_l_sec = None
                    
                    for chunk in local_result.chunks:
                        if chunk.label.lower() in ["section", "header", "heading"]:
                            current_l_sec = {
                                "id": chunk.id,
                                "title": chunk.content,
                                "clauses": []
                            }
                            local_sections.append(current_l_sec)
                        else:
                            if not current_l_sec:
                                current_l_sec = {
                                    "id": f"sec-default-{path}",
                                    "title": "General Requirements",
                                    "clauses": []
                                }
                                local_sections.append(current_l_sec)
                            current_l_sec["clauses"].append({
                                "id": chunk.id,
                                "number": chunk.properties.get("number", "Generic"),
                                "text": chunk.content,
                                "label": chunk.label
                            })
                    state["chunks"][path] = {"sop_id": path, "sections": local_sections}
            except Exception as e:
                state["errors"].append(f"LLM Chunking Agent skipped (details: {e}). Falling back to ChunkerService.")
                llm_chunk_working = False
                
            if not llm_chunk_working:
                # Deterministic static fallback
                state["chunks"]["global"] = ChunkerService.chunk_document("global_sop", state["raw_texts"]["global"])
                for path in local_paths:
                    state["chunks"][path] = ChunkerService.chunk_document(path, state["raw_texts"][path])
            
            # Exact match document check: If local text is identical to global standard text, clone the chunk structure
            for path in local_paths:
                if state["raw_texts"][path].strip() == state["raw_texts"]["global"].strip():
                    import copy
                    state["chunks"][path] = copy.deepcopy(state["chunks"]["global"])
                    state["chunks"][path]["sop_id"] = path
                    # Assign unique local IDs to avoid database key collision
                    for sec in state["chunks"][path]["sections"]:
                        sec["id"] = f"{sec['id']}-local"
                        for cls in sec.get("clauses", []):
                            cls["id"] = f"{cls['id']}-local"
        except Exception as e:
            state["status"] = "failed"
            state["errors"].append(f"Chunking stage failed: {str(e)}")
            if callback: callback(state)
            return state

        # Step 3: Relationship Inference and Graph Writing
        try:
            state["stage"] = "graph-written"
            state["progress"] = 60
            if callback: callback(state)
            nodes_to_write = []
            relationships_to_write = []
            import os
            
            # Prepare Global Base SOP node
            nodes_to_write.append({
                "label": "SOP",
                "id": "global_sop",
                "properties": {"name": "Global SOP", "type": "Global"}
            })
            
            # Prepare Local SOP nodes
            for path in local_paths:
                nodes_to_write.append({
                    "label": "SOP",
                    "id": path,
                    "properties": {"name": os.path.basename(path), "type": "Local"}
                })
            
            llm_working = True
            
            # Define a robust retry wrapper for each chunk (prevents single-chunk errors from resetting the run)
            def infer_with_retries(chunk_id, chunk_content, parent_context, sibling_context, candidate_pairs):
                retries = 3
                for attempt in range(retries):
                    try:
                        return self.inference.infer_relationships(
                            chunk_id=chunk_id,
                            chunk_content=chunk_content,
                            parent_context=parent_context,
                            sibling_context=sibling_context,
                            candidate_pairs=candidate_pairs
                        )
                    except Exception as e:
                        if attempt < retries - 1:
                            time.sleep(1.0)
                        else:
                            from agents.relationship_inference import SemanticNodeMapping
                            state["errors"].append(f"Failed to infer relationships for chunk {chunk_id} after {retries} retries: {str(e)}")
                            return SemanticNodeMapping(
                                chunk_id=chunk_id,
                                node_type="Clause" if "clause" in str(parent_context).lower() else "Section",
                                properties={},
                                relationships=[]
                            )

            # 1. Run LLM Relationship Inference Agent on Global SOP chunks
            try:
                from concurrent.futures import ThreadPoolExecutor
                
                for sec in state["chunks"]["global"]["sections"]:
                    siblings = [s["title"] for s in state["chunks"]["global"]["sections"] if s["id"] != sec["id"]]
                    
                    sec_mapping = infer_with_retries(
                        chunk_id=sec["id"],
                        chunk_content=sec["title"],
                        parent_context={"sop_type": "Global"},
                        sibling_context=siblings,
                        candidate_pairs=[]
                    )
                    
                    nodes_to_write.append({
                        "label": sec_mapping.node_type or "Section",
                        "id": sec_mapping.chunk_id,
                        "properties": sec_mapping.properties or {"title": sec["title"]}
                    })
                    relationships_to_write.append({
                        "source_id": "global_sop",
                        "target_id": sec["id"],
                        "type": "HAS_SECTION",
                        "properties": {}
                    })
                    
                    clauses_to_process = sec["clauses"]
                    
                    def process_single_global_clause(cls):
                        cls_siblings = [{"id": c["id"], "number": c["number"], "text": c["text"]} for c in sec["clauses"] if c["id"] != cls["id"]]
                        cls_mapping = infer_with_retries(
                            chunk_id=cls["id"],
                            chunk_content=cls["text"],
                            parent_context={"section_title": sec["title"]},
                            sibling_context=cls_siblings,
                            candidate_pairs=[]
                        )
                        return cls, cls_mapping
                        
                    with ThreadPoolExecutor(max_workers=8) as executor:
                        results = list(executor.map(process_single_global_clause, clauses_to_process))
                        
                    for cls, cls_mapping in results:
                        nodes_to_write.append({
                            "label": cls_mapping.node_type or "Clause",
                            "id": cls_mapping.chunk_id,
                            "properties": cls_mapping.properties or {"number": cls["number"], "text": cls["text"]}
                        })
                        relationships_to_write.append({
                            "source_id": sec["id"],
                            "target_id": cls["id"],
                            "type": "HAS_CLAUSE",
                            "properties": {}
                        })
                        
                        for rel in cls_mapping.relationships:
                            if rel.target_chunk_id and rel.relationship_type:
                                relationships_to_write.append({
                                    "source_id": cls_mapping.chunk_id,
                                    "target_id": rel.target_chunk_id,
                                    "type": rel.relationship_type,
                                    "properties": {
                                        "confidence": rel.confidence,
                                        "rationale": rel.rationale,
                                        "diffType": rel.diff_type
                                    }
                                })
                
                # Write Global Standard nodes/relationships to Neo4j first so they exist for local query MATCHes
                try:
                    self.writer.write_agent_output(nodes_to_write, relationships_to_write)
                    nodes_to_write = []
                    relationships_to_write = []
                except Exception as e:
                    state["errors"].append(f"Neo4j Global Write warning: {e}. Project will proceed in-memory.")
                
                # 2. Run LLM Relationship Inference Agent on Local SOP chunks (comparing them to global standard candidates)
                global_clauses = []
                for g_sec in state["chunks"]["global"]["sections"]:
                    for g_cls in g_sec.get("clauses", []):
                        global_clauses.append({
                            "id": g_cls["id"],
                            "number": g_cls["number"],
                            "text": g_cls["text"]
                        })
                
                from concurrent.futures import ThreadPoolExecutor
                
                for path in local_paths:
                    local_sop_data = state["chunks"].get(path, {})
                    for sec in local_sop_data.get("sections", []):
                        sec_siblings = [s["title"] for s in local_sop_data.get("sections", []) if s["id"] != sec["id"]]
                        
                        sec_mapping = infer_with_retries(
                            chunk_id=sec["id"],
                            chunk_content=sec["title"],
                            parent_context={"sop_type": "Local", "file": path},
                            sibling_context=sec_siblings,
                            candidate_pairs=[]
                        )
                        
                        nodes_to_write.append({
                            "label": sec_mapping.node_type or "Section",
                            "id": sec_mapping.chunk_id,
                            "properties": sec_mapping.properties or {"title": sec["title"]}
                        })
                        relationships_to_write.append({
                            "source_id": path,
                            "target_id": sec["id"],
                            "type": "HAS_SECTION",
                            "properties": {}
                        })
                        
                        clauses_to_process = sec.get("clauses", [])
                        
                        def process_single_local_clause(cls):
                            cls_siblings = [{"id": c["id"], "number": c["number"], "text": c["text"]} for c in sec.get("clauses", []) if c["id"] != cls["id"]]
                            
                            from graph.retrieval_service import GraphRetrievalService
                            from agents.validation_agent import ValidationAgent
                            
                            retriever = GraphRetrievalService()
                            db_candidates = retriever.retrieve_candidates(cls["text"], embedding=None, limit=3)
                            retriever.close()
                            
                            candidates = ValidationAgent.validate_candidates(db_candidates, {"section_title": sec["title"]})
                            
                            if not candidates:
                                best_match_gcls = None
                                best_score = -1.0
                                for g_cls in global_clauses:
                                    comp_res = self.comparison.compare_clauses(cls["text"], g_cls["text"])
                                    if comp_res["combined_score"] > best_score:
                                        best_score = comp_res["combined_score"]
                                        best_match_gcls = g_cls
                                candidates = [best_match_gcls] if best_match_gcls else []
                            
                            cls_mapping = infer_with_retries(
                                chunk_id=cls["id"],
                                chunk_content=cls["text"],
                                parent_context={"section_title": sec["title"], "file": path},
                                sibling_context=cls_siblings,
                                candidate_pairs=candidates
                            )
                            return cls, cls_mapping
                            
                        with ThreadPoolExecutor(max_workers=8) as executor:
                            results = list(executor.map(process_single_local_clause, clauses_to_process))
                            
                        for cls, cls_mapping in results:
                            nodes_to_write.append({
                                "label": cls_mapping.node_type or "Clause",
                                "id": cls_mapping.chunk_id,
                                "properties": cls_mapping.properties or {"number": cls["number"], "text": cls["text"]}
                            })
                            relationships_to_write.append({
                                "source_id": sec["id"],
                                "target_id": cls["id"],
                                "type": "HAS_CLAUSE",
                                "properties": {}
                            })
                            
                            for rel in cls_mapping.relationships:
                                if rel.target_chunk_id and rel.relationship_type:
                                    conf = rel.confidence if rel.confidence is not None else 1.0
                                    rel_status = "APPROVED" if conf >= 0.70 else "PENDING_REVIEW"
                                    relationships_to_write.append({
                                        "source_id": cls_mapping.chunk_id,
                                        "target_id": rel.target_chunk_id,
                                        "type": rel.relationship_type if rel_status == "APPROVED" else "PENDING_REVIEW",
                                        "properties": {
                                            "confidence": conf,
                                            "rationale": rel.rationale,
                                            "diffType": rel.diff_type,
                                            "status": rel_status
                                        }
                                    })
            except Exception as e:
                state["errors"].append(f"LLM Relationship Inference Agent skipped (details: {e}). Falling back to static template.")
                llm_working = False
                
            if not llm_working:
                # Deterministic static fallback if LLM has no key
                # A. Write Global
                for sec in state["chunks"]["global"]["sections"]:
                    nodes_to_write.append({
                        "label": "Section",
                        "id": sec["id"],
                        "properties": {"title": sec["title"]}
                    })
                    relationships_to_write.append({
                        "source_id": "global_sop",
                        "target_id": sec["id"],
                        "type": "HAS_SECTION",
                        "properties": {}
                    })
                    for cls in sec["clauses"]:
                        nodes_to_write.append({
                            "label": "Clause",
                            "id": cls["id"],
                            "properties": {"number": cls["number"], "text": cls["text"]}
                        })
                        relationships_to_write.append({
                            "source_id": sec["id"],
                            "target_id": cls["id"],
                            "type": "HAS_CLAUSE",
                            "properties": {}
                        })
                # B. Write Locals (Static structure fallback)
                for path in local_paths:
                    local_sop_data = state["chunks"].get(path, {})
                    for sec in local_sop_data.get("sections", []):
                        nodes_to_write.append({
                            "label": "Section",
                            "id": sec["id"],
                            "properties": {"title": sec["title"]}
                        })
                        relationships_to_write.append({
                            "source_id": path,
                            "target_id": sec["id"],
                            "type": "HAS_SECTION",
                            "properties": {}
                        })
                        for cls in sec.get("clauses", []):
                            nodes_to_write.append({
                                "label": "Clause",
                                "id": cls["id"],
                                "properties": {"number": cls["number"], "text": cls["text"]}
                            })
                            relationships_to_write.append({
                                "source_id": sec["id"],
                                "target_id": cls["id"],
                                "type": "HAS_CLAUSE",
                                "properties": {}
                            })

            # Attempt writing graph (survive if Neo4j is offline)
            try:
                self.writer.write_agent_output(nodes_to_write, relationships_to_write)
            except Exception as e:
                state["errors"].append(f"Neo4j Write warning: {e}. Project will proceed in-memory.")
                
        except Exception as e:
            state["status"] = "failed"
            state["errors"].append(f"Graph writing pipeline failed: {str(e)}")
            if callback: callback(state)
            return state

        # Step 4: Comparison & Validity
        try:
            state["stage"] = "compared"
            state["progress"] = 80
            if callback: callback(state)
            
            global_sections = state["chunks"].get("global", {}).get("sections", [])
            global_clauses = []
            for sec in global_sections:
                for cls in sec.get("clauses", []):
                    global_clauses.append(cls)
            
            if not global_clauses:
                raise ValueError("Global SOP does not contain any valid clauses for comparison. Please check document structure.")
                
            # Perform semantic matching for each local clause against ALL global clauses to find the best fit
            for path in local_paths:
                local_sections = state["chunks"].get(path, {}).get("sections", [])
                for sec in local_sections:
                    for cls in sec.get("clauses", []):
                        
                        best_match_clause_id = None
                        best_score = -1.0
                        best_res = None
                        
                        best_match_clause_id, best_res = self.comparison.find_best_match_graph_rag(cls, global_clauses)
                        
                        if best_match_clause_id:
                            state["comparison_results"].append({
                                "local_sop_path": path,
                                "local_clause_id": cls["id"],
                                "global_clause_id": best_match_clause_id,
                                "similarity": best_res["combined_score"],
                                "lexical": best_res["lexical_similarity"],
                                "semantic": best_res["semantic_similarity"]
                            })
        except Exception as e:
            state["status"] = "failed"
            state["errors"].append(f"Comparison stage failed: {str(e)}")
            if callback: callback(state)
            return state

        # Step 5: Scoring and Report
        try:
            state["stage"] = "done"
            state["progress"] = 90
            if callback: callback(state)
            
            import os
            sop_results = {}
            best_match_sop = None
            best_match_score = -1.0
            
            global_sections = state["chunks"].get("global", {}).get("sections", [])
            
            for path in local_paths:
                filename = os.path.basename(path)
                # Filter comparison results for this local SOP
                sop_comps = [c for c in state["comparison_results"] if c.get("local_sop_path") == path]
                
                if sop_comps:
                    avg_sim = sum(c["similarity"] for c in sop_comps) / len(sop_comps)
                else:
                    avg_sim = 0.5
                
                sim_percentage = round(avg_sim * 100, 1)
                
                # Calculate dynamic necessity score (percentage of deviations that are justified)
                justified_count = 0
                total_comps = len(sop_comps)
                
                # Dynamic recommendations list based on actual mismatches
                recs = []
                mismatch_idx = 1
                
                local_sections = state["chunks"].get(path, {}).get("sections", [])
                
                from concurrent.futures import ThreadPoolExecutor
                
                audit_tasks = []
                for comp in sop_comps:
                    if comp["similarity"] < 1.0:
                        local_text = ""
                        global_text = ""
                        clause_num = "Generic"
                        local_section = "General"
                        for sec in local_sections:
                            for c in sec.get("clauses", []):
                                if c["id"] == comp["local_clause_id"]:
                                    local_text = c["text"]
                                    clause_num = c.get("number", "Generic")
                                    local_section = sec.get("title", "General")
                                    break
                                    
                        global_section = "General"
                        for sec in global_sections:
                            for c in sec.get("clauses", []):
                                if c["id"] == comp["global_clause_id"]:
                                    global_text = c["text"]
                                    global_section = sec.get("title", "General")
                                    break
                        
                        if local_text and global_text:
                            audit_tasks.append({
                                "local_text": local_text,
                                "global_text": global_text,
                                "clause_num": clause_num,
                                "local_section": local_section,
                                "global_section": global_section
                            })
                            
                def run_audit(task, idx):
                    audit = self.audit_clause_deviation(task["local_text"], task["global_text"], filename)
                    return {
                        "clause_number": f"{task['clause_num']} (Mismatch {idx})",
                        "action": audit["action"],
                        "justification": audit["justification"],
                        "global_text": task["global_text"],
                        "local_text": task["local_text"],
                        "global_section": task["global_section"],
                        "local_section": task["local_section"]
                    }
                
                with ThreadPoolExecutor(max_workers=6) as executor:
                    futures = [executor.submit(run_audit, task, idx + 1) for idx, task in enumerate(audit_tasks)]
                    results = [fut.result() for fut in futures]
                    
                for res in results:
                    if res["action"].lower() == "keep":
                        justified_count += 1
                    recs.append(res)
                
                necessity_score = ScoringService.calculate_necessity_score(max(total_comps, 1), justified_count)
                nec_percentage = round(necessity_score * 100, 1) if total_comps > 0 else 0.0
                sim_percentage = sim_percentage if total_comps > 0 else 0.0
                
                sop_results[path] = {
                    "name": filename,
                    "similarity_score": sim_percentage,
                    "necessity_score": nec_percentage,
                    "recommendations": recs,
                    "total_clauses": total_comps
                }
                
                if total_comps > 0 and sim_percentage > best_match_score:
                    best_match_score = sim_percentage
                    best_match_sop = filename
            
            state["report"] = {
                "summary": f"Successfully compared {len(local_paths)} Local SOP(s) against the Global Standard.",
                "best_match": {
                    "name": best_match_sop or "N/A",
                    "similarity_score": best_match_score if best_match_score >= 0 else 0.0
                },
                "sop_results": sop_results
            }
        except Exception as e:
            state["status"] = "failed"
            state["errors"].append(f"Report generation stage failed: {str(e)}")
            if callback: callback(state)
            return state

        state["status"] = "completed"
        state["progress"] = 100
        if callback: callback(state)
        return state

    def audit_clause_deviation(self, local_text: str, global_text: str, filename: str) -> dict:
        """Calls the LLM to dynamically compare the local deviation against the global standard, deciding the action and justification."""
        from llm.factory import LLMFactory
        from langchain_core.prompts import ChatPromptTemplate
        from pydantic import BaseModel, Field
        
        class AuditDecision(BaseModel):
            action: str = Field(description="Action recommendation: keep, retire, merge, or sme review")
            justification: str = Field(description="Dynamic, context-aware justification explaining why this local change is kept, retired, or merged.")
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are an expert Regulatory Compliance Auditor.
            Compare the local SOP clause against the global standard clause.
            Decide if the local clause should be:
            1. 'keep': If the deviation is a valid local site-specific adjustment.
            2. 'retire': If the deviation is unnecessary, unsafe, or should align with the global rule.
            3. 'merge': If both rules contain important elements that should be combined.
            4. 'sme review': If the deviation is highly critical and requires manual expert review.
            
            Provide a clear, context-sensitive justification.
            """),
            ("user", "Document Context: {filename}\nGlobal Clause: \"{global_text}\"\nLocal Clause: \"{local_text}\"")
        ])
        
        try:
            model = LLMFactory.get_chat_model()
            structured_llm = model.with_structured_output(AuditDecision)
            chain = prompt | structured_llm
            res = chain.invoke({
                "filename": filename,
                "global_text": global_text,
                "local_text": local_text
            })
            return {
                "action": res.action,
                "justification": res.justification
            }
        except Exception as e:
            # Fallback if LLM fails or is unconfigured
            return {
                "action": "sme review",
                "justification": f"Automated audit fallback. Detected semantic difference between local rules in {filename} and global standard."
            }