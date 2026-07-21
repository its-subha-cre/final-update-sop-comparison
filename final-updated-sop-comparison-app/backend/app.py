import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import config_instance
from api.config import config_bp
from agents.orchestrator import PipelineOrchestrator
import re
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Register blueprints
app.register_blueprint(config_bp, url_prefix='/api/config')

# In-memory storage for pipeline runs and statuses
pipeline_jobs = {}

# Set upload folders
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
GLOBAL_UPLOAD_DIR = os.path.join(UPLOAD_FOLDER, 'global')
LOCAL_UPLOAD_DIR = os.path.join(UPLOAD_FOLDER, 'local')
JOBS_FILE = os.path.join(UPLOAD_FOLDER, 'pipeline_jobs.json')

import json

def save_jobs_to_disk():
    try:
        serializable = {}
        for job_id, job in pipeline_jobs.items():
            serializable[job_id] = {k: v for k, v in job.items() if k != '_thread'}
        with open(JOBS_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        print(f"Error saving jobs: {e}")

def load_jobs_from_disk():
    global pipeline_jobs
    try:
        if os.path.exists(JOBS_FILE):
            with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                pipeline_jobs.update(json.load(f))
    except Exception as e:
        print(f"Error loading jobs: {e}")

load_jobs_from_disk()

os.makedirs(GLOBAL_UPLOAD_DIR, exist_ok=True)
os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.docx'}

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handles multi-file uploads for both Global SOP and Local SOP slots."""
    slot = request.form.get('slot')  # 'global' or 'local'
    if slot not in ['global', 'local']:
        return jsonify({"success": False, "message": "Invalid upload slot specified. Must be 'global' or 'local'."}), 400

    if 'files' not in request.files:
        return jsonify({"success": False, "message": "No files found in request."}), 400

    files = request.files.getlist('files')
    saved_files = []
    
    target_dir = GLOBAL_UPLOAD_DIR if slot == 'global' else LOCAL_UPLOAD_DIR

    for file in files:
        if file and allowed_file(file.filename):
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            filepath = os.path.join(target_dir, filename)
            file.save(filepath)
            saved_files.append({
                "original_name": file.filename,
                "saved_path": filepath
            })
        else:
            return jsonify({
                "success": False, 
                "message": f"File type not allowed or empty file. Acceptable formats: {list(ALLOWED_EXTENSIONS)}"
            }), 400

    return jsonify({
        "success": True,
        "slot": slot,
        "files": saved_files
    })

@app.route('/api/compare/run', methods=['POST'])
def run_comparison():
    """Starts the comparison pipeline job asynchronously using in-memory threads."""
    data = request.json or {}
    global_file = data.get('globalFile')
    local_files = data.get('localFiles', [])
    
    if not global_file or not local_files:
        return jsonify({
            "success": False,
            "message": "Both globalFile path and at least one localFiles path are required."
        }), 400

    job_id = str(uuid.uuid4())
    
    # Initialize job tracking state
    pipeline_jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued",
        "errors": [],
        "report": {},
        "progress": 0
    }
    save_jobs_to_disk()

    # Internal worker function to run pipeline in thread
    def worker():
        orchestrator = PipelineOrchestrator()
        pipeline_jobs[job_id]["status"] = "in_progress"
        save_jobs_to_disk()
        
        def progress_callback(current_state):
            pipeline_jobs[job_id].update({
                "stage": current_state.get("stage"),
                "progress": current_state.get("progress"),
                "errors": current_state.get("errors")
            })
            save_jobs_to_disk()

        try:
            result = orchestrator.run_pipeline(
                global_path=global_file, 
                local_paths=local_files,
                callback=progress_callback
            )
            pipeline_jobs[job_id].update(result)
            save_jobs_to_disk()
        except Exception as e:
            pipeline_jobs[job_id]["status"] = "failed"
            pipeline_jobs[job_id]["errors"].append(str(e))
            save_jobs_to_disk()

    # Trigger worker asynchronously (using threading for local environment reliability)
    import threading
    thread = threading.Thread(target=worker)
    thread.start()

    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "Comparison pipeline triggered successfully."
    })

@app.route('/api/compare/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Retrieves pipeline execution status and results."""
    job = pipeline_jobs.get(job_id)
    if not job:
        return jsonify({"success": False, "message": f"Job ID {job_id} not found."}), 404
        
    return jsonify({
        "success": True,
        "job": job
    })

@app.route('/api/chat', methods=['POST'])
def chat_assistant():
    """Provides LLM response about SOP comparison results and raw document context."""
    from llm.factory import LLMFactory
    
    data = request.json or {}
    message = data.get('message')
    job_id = data.get('jobId')
    history = data.get('history', [])
    
    if not message:
        return jsonify({"success": False, "message": "Message parameter is required."}), 400
        
    # --- DOMAIN GUARDRAIL LAYER ---
    valid_keywords = [
        "sop", "compliance", "mismatch", "recommendation", "finding", "audit",
        "dashboard", "report", "clause", "section", "deviation", "global", "local",
        "similarity", "document", "regulatory", "procedure", "standard", "policy",
        "guideline", "site", "xray", "workflow", "matrix", "analysis", "failed",
        "passed", "violation", "issue", "score", "relationship", "graph", "neo4j"
    ]
    query_lower = message.lower()
    is_definitely_valid = any(kw in query_lower for kw in valid_keywords)
    
    if not is_definitely_valid:
        try:
            from llm.factory import LLMFactory
            classifier_model = LLMFactory.get_chat_model()
            from langchain_core.messages import SystemMessage, HumanMessage
            classification_prompt = (
                "You are a domain classifier for an SOP Compliance Platform.\n"
                "Determine if the user's input is related to: Standard Operating Procedures (SOPs), "
                "corporate policies, document compliance, comparisons, regulations, audit findings, "
                "dashboard metrics, or this specific comparison application.\n"
                "Respond with exactly one word: 'VALID' or 'INVALID'."
            )
            res = classifier_model.invoke([
                SystemMessage(content=classification_prompt),
                HumanMessage(content=message)
            ])
            verdict = res.content.strip().upper()
            if "INVALID" in verdict:
                return jsonify({
                    "success": True,
                    "response": "I am your SOP Compliance Assistant. I can only help with questions related to Standard Operating Procedures (SOPs), compliance analysis, comparison results, audit findings, recommendations, uploaded SOP documents, and dashboard metrics. Please ask a question related to your SOP Compliance Platform."
                })
        except Exception:
            pass # Fallback to existing chat flow if classification fails
        
    # --- CONFIGURABLE LIMITS ---
    MAX_CONTEXT_CHUNKS = 3
    MAX_CHAT_HISTORY = 4
    MAX_CONTEXT_CHARACTERS = 3000
    TOKEN_SAFETY_MARGIN = 400
    MODEL_TOKEN_LIMIT = 6000
    
    nodes_info = []
    relationships_info = []
    
    # 1. Fetch active job with memory & disk fallback support (fixes Problem 1)
    active_job = None
    if job_id and job_id in pipeline_jobs:
        active_job = pipeline_jobs[job_id]
    else:
        # Fallback to the latest completed job
        completed_jobs = [j for j in pipeline_jobs.values() if j.get("status") == "completed"]
        if completed_jobs:
            active_job = completed_jobs[-1]

    # Clean local SOP records from active job
    local_sops = []
    if active_job:
        report = active_job.get("report", {})
        sop_results = report.get("sop_results", {})
        for path, data in sop_results.items():
            local_sops.append({
                "path": path,
                "name": data.get("name"),
                "similarity_score": data.get("similarity_score"),
                "necessity_score": data.get("necessity_score"),
                "total_clauses": data.get("total_clauses"),
                "recommendations": data.get("recommendations", [])
            })
            
    # Build a platform repository metadata context block for prompt grounding
    platform_metadata = "=== ACTIVE PLATFORM REPOSITORY METADATA ===\n"
    try:
        disk_global = []
        if os.path.exists(GLOBAL_UPLOAD_DIR):
            disk_global = [f for f in os.listdir(GLOBAL_UPLOAD_DIR) if f != '.gitkeep' and not f.startswith('.')]
        disk_local = []
        if os.path.exists(LOCAL_UPLOAD_DIR):
            disk_local = [f for f in os.listdir(LOCAL_UPLOAD_DIR) if f != '.gitkeep' and not f.startswith('.')]
            
        platform_metadata += f"- Total Uploaded Local SOPs on disk: {len(disk_local)}\n"
        if disk_local:
            platform_metadata += f"- Uploaded Local SOP Filenames: {', '.join(disk_local)}\n"
        if disk_global:
            platform_metadata += f"- Uploaded Global SOP Filename: {disk_global[0]}\n"
    except Exception as e:
        platform_metadata += f"- Disk metadata read warning: {str(e)}\n"
        
    if active_job:
        rep = active_job.get("report", {})
        best_match = rep.get("best_match", {})
        platform_metadata += f"- Comparison Job Status: {active_job.get('status')}\n"
        if best_match.get('name'):
            platform_metadata += f"- Best Match SOP: {best_match.get('name')} ({best_match.get('similarity_score', 0)}% similarity)\n"
    else:
        platform_metadata += "- No active comparison results loaded yet.\n"
    platform_metadata += "==========================================\n"

    # 2. Conversational context target SOP resolution (fixes Problem 4)
    def find_target_sop_in_text(txt):
        if not txt:
            return None
        txt_lower = txt.lower()
        
        # If there is only one local SOP, default to it for generic references
        if len(local_sops) == 1:
            generic_ref = ["local", "sop", "file", "deviation", "mismatch", "recommendation", "document", "this"]
            if any(ref in txt_lower for ref in generic_ref):
                return local_sops[0]
                
        for sop in local_sops:
            filename = sop["name"].lower()
            clean_name = filename
            if "_" in filename:
                clean_name = filename.split("_", 1)[1]
            clean_name = clean_name.replace(".docx", "").replace(".pdf", "").replace("-", " ").replace("_", " ")
            
            # Simple alias checks
            aliases = [clean_name, clean_name.replace("lsop", "").strip(), clean_name.replace("xray", "").strip()]
            
            # Add all alphanumeric tokens of length >= 3 from clean name
            tokens = [t for t in re.split(r'\s+', clean_name) if len(t) >= 3]
            aliases.extend(tokens)
            
            site_match = re.search(r'site\s*0*(\d+)', clean_name)
            if site_match:
                num = site_match.group(1)
                aliases.extend([f"site {num}", f"site 0{num}", f"site0{num}", f"site{num}"])
                
            for alias in aliases:
                if alias and alias in txt_lower:
                    return sop
        return None

    # Check current query first, then history backwards (fixes conversational context)
    target_sop = find_target_sop_in_text(message)
    if not target_sop:
        for msg in reversed(history):
            content = msg.get('content', '')
            found = find_target_sop_in_text(content)
            if found:
                target_sop = found
                break

    # 3. Router logic: check if this is a compliance/mismatch query (Intelligent Query Routing)
    compliance_keywords = [
        "mismatch", "recommendation", "finding", "compliance score", "similarity score",
        "failed section", "passed section", "dashboard", "report", "audit", "issue",
        "violation", "deviation", "highest", "compliant", "list local", "how many local"
    ]
    is_compliance_query = any(kw in message.lower() for kw in compliance_keywords)

    job_context = ""
    graph_context = ""
    detailed_recs = []

    if is_compliance_query:
        # --- PATH A: COMPLIANCE RESULTS (Source 2) ---
        # Resolve Mismatch Number Queries (fixes Problem 2 & 5)
        match_num = re.search(r'mismatch\s*(?:number)?\s*(\d+)', message.lower())
        
        summary_ctx = "Compliance Results Context (Directly from UI Mismatch List):\n"
        if active_job:
            rep = active_job.get('report', {})
            summary_ctx += f"- Active Summary: {rep.get('summary')}\n"
            summary_ctx += f"- Best Match: {rep.get('best_match', {}).get('name')} ({rep.get('best_match', {}).get('similarity_score')}%)\n"
            summary_ctx += f"- Available Local SOPs: {', '.join(s['name'] for s in local_sops)}\n"
        else:
            summary_ctx += "- No active comparison report found in memory. Please tell the user to run an analysis first.\n"
            
        # Target details for Mismatch Number Queries
        if match_num and target_sop:
            num = int(match_num.group(1))
            recs = target_sop["recommendations"]
            if 1 <= num <= len(recs):
                r = recs[num - 1]
                summary_ctx += f"\n[MATCH FOUND] Target Mismatch Details:\n"
                summary_ctx += f"- SOP Document: {target_sop['name']}\n"
                summary_ctx += f"- Mismatch Number: {num}\n"
                summary_ctx += f"- Clause Reference: {r.get('clause_number')}\n"
                summary_ctx += f"- Section Location: {r.get('local_section')}\n"
                summary_ctx += f"- Global SOP Section: {r.get('global_section')}\n"
                summary_ctx += f"- Action: {r.get('action')}\n"
                summary_ctx += f"- Global SOP Text: \"{r.get('global_text')}\"\n"
                summary_ctx += f"- Local SOP Text: \"{r.get('local_text')}\"\n"
                summary_ctx += f"- Justification/Rationale: {r.get('justification')}\n"
            else:
                summary_ctx += f"\n[MATCH ERROR] User asked for Mismatch {num} of {target_sop['name']}, but it only has {len(recs)} mismatches.\n"
        
        # General list of mismatches (fixes Problem 3 - unlimited mismatches summarized)
        else:
            if target_sop:
                summary_ctx += f"\nAll Mismatches & Recommendations for {target_sop['name']} (Necessity Score: {target_sop['necessity_score']}%, Similarity: {target_sop['similarity_score']}%):\n"
                for idx, r in enumerate(target_sop["recommendations"]):
                    detailed_recs.append({
                        "file": target_sop['name'],
                        "clause": r.get("clause_number"),
                        "action": r.get("action"),
                        "global": r.get("global_text")[:120] if r.get("global_text") else "",
                        "local": r.get("local_text")[:120] if r.get("local_text") else "",
                        "rationale": r.get("justification")[:120] if r.get("justification") else ""
                    })
            else:
                # Include all local SOP results (fixes Problem 3 - dynamic lists)
                for sop in local_sops:
                    summary_ctx += f"\nSOP Document: {sop['name']} (Similarity: {sop['similarity_score']}%, Necessity: {sop['necessity_score']}%)\n"
                    for idx, r in enumerate(sop["recommendations"]):
                        detailed_recs.append({
                            "file": sop['name'],
                            "clause": r.get("clause_number"),
                            "action": r.get("action"),
                            "global": r.get("global_text")[:80] if r.get("global_text") else "",
                            "local": r.get("local_text")[:80] if r.get("local_text") else "",
                            "rationale": r.get("justification")[:80] if r.get("justification") else ""
                        })
                        
        job_context = summary_ctx

    else:
        # --- PATH B: GRAPH / NEOP4J RAG (Source 1) ---
        try:
            from graph.retrieval_service import GraphRetrievalService
            retriever = GraphRetrievalService()
            db_candidates = retriever.retrieve_candidates(message, embedding=None, limit=MAX_CONTEXT_CHUNKS)
            retriever.close()
            
            if db_candidates:
                graph_context = "\n- RETRIEVED NEO4J GRAPH COMPLIANCE KNOWLEDGE:\n"
                for cand in db_candidates:
                    cand_id = cand.get('id', 'N/A')
                    cand_num = cand.get('number', 'N/A')
                    cand_text = cand.get('text', '')
                    graph_context += f"  * [Node: {cand_id}] Clause {cand_num}: {cand_text}\n"
                    nodes_info.append({
                        "id": cand_id,
                        "label": "Clause",
                        "properties": {"number": cand_num, "text": cand_text}
                    })
            
            from neo4j import GraphDatabase
            from config import config_instance
            driver = GraphDatabase.driver(config_instance.NEO4J_URI, auth=(config_instance.NEO4J_USER, config_instance.NEO4J_PASSWORD))
            with driver.session() as session:
                # 1. Fetch targeted sections/clauses if target SOP is resolved
                if target_sop:
                    target_filename = target_sop["name"]
                    sop_query = """
                    MATCH (sop:SOP)-[:HAS_SECTION]->(sec:Section)
                    WHERE toLower(sop.name) = toLower($filename) OR toLower(sop.id) CONTAINS toLower($filename)
                    OPTIONAL MATCH (sec)-->(c)
                    RETURN sec.title as section_title, labels(c)[0] as c_label, coalesce(c.number, properties(c)["number"], "") as clause_number, 
                           coalesce(c.text, c.content, c.title, "") as clause_text, properties(c) as c_props
                    LIMIT 35
                    """
                    res = session.run(sop_query, filename=target_filename)
                    sec_clauses = {}
                    for record in res:
                        sec_title = record["section_title"]
                        c_label = record["c_label"] or "Clause"
                        c_num = record["clause_number"]
                        c_text = record["clause_text"]
                        c_props = record["c_props"] or {}
                        
                        if not c_text and c_props:
                            # Fallback to any text property in properties(c)
                            str_vals = [str(v) for k, v in c_props.items() if k not in ["id", "number"] and isinstance(v, str)]
                            if str_vals:
                                c_text = " ".join(str_vals)
                                
                        if sec_title not in sec_clauses:
                            sec_clauses[sec_title] = []
                        if c_text:
                            num_str = f"Clause {c_num}: " if c_num else f"[{c_label}]: "
                            sec_clauses[sec_title].append(f"{num_str}{c_text}")
                    
                    if sec_clauses:
                        graph_context = f"\n- RETRIEVED GRAPH DETAILS FOR SOP {target_filename}:\n"
                        for sec_title, clauses in sec_clauses.items():
                            graph_context += f"  * Section: {sec_title}\n"
                            for cl in clauses[:6]: # Respect token limit constraints
                                graph_context += f"    - {cl}\n"
                                
                # 2. General keyword search for supplementary relationships (filtering generic tokens)
                keywords = [w for w in re.findall(r'\w+', message.lower()) if len(w) >= 3 or w.isdigit()]
                exclude_kws = {"local", "sop", "section", "clause", "document", "tell", "about", "the", "what", "where", "have", "uploaded", "and", "for", "with", "this", "procedure", "procedures", "detail", "details"}
                filtered_kws = [w for w in keywords if w not in exclude_kws]
                
                if filtered_kws:
                    rel_query = """
                    MATCH (n)-[r]->(m)
                    WHERE any(kw in $kws WHERE toLower(n.text) CONTAINS kw OR toLower(m.text) CONTAINS kw or toLower(n.id) CONTAINS kw or toLower(m.id) CONTAINS kw or toLower(n.title) CONTAINS kw or toLower(m.title) CONTAINS kw or toLower(n.name) CONTAINS kw or toLower(m.name) CONTAINS kw)
                    RETURN labels(n)[0] as s_label, n.id as s_id, properties(n) as s_props,
                           type(r) as r_type, r.confidence as r_conf, r.rationale as r_rat,
                           labels(m)[0] as t_label, m.id as t_id, properties(m) as t_props
                    LIMIT 8
                    """
                    res = session.run(rel_query, kws=filtered_kws)
                    rel_text_blocks = []
                    for record in res:
                        s_props = record["s_props"] or {}
                        t_props = record["t_props"] or {}
                        s_val = s_props.get("text") or s_props.get("title") or s_props.get("name") or ""
                        t_val = t_props.get("text") or t_props.get("title") or t_props.get("name") or ""
                        s_str = f"\"{s_val[:120]}\"" if s_val else "N/A"
                        t_str = f"\"{t_val[:120]}\"" if t_val else "N/A"
                        
                        rel_text_blocks.append(f"  * Node ({record['s_id']}:{record['s_label']} Content: {s_str}) --[{record['r_type']}]--> Node ({record['t_id']}:{record['t_label']} Content: {t_str}) (Rationale: {record['r_rat'] or 'N/A'})")
                        relationships_info.append({
                            "source": record['s_id'],
                            "target": record['t_id'],
                            "type": record['r_type'],
                            "properties": {"confidence": record['r_conf'], "rationale": record['r_rat']}
                        })
                        nodes_info.append({"id": record['s_id'], "label": record['s_label'], "properties": s_props})
                        nodes_info.append({"id": record['t_id'], "label": record['t_label'], "properties": t_props})
                    if rel_text_blocks:
                        graph_context += "\n- RETRIEVED KNOWLEDGE GRAPH RELATIONSHIPS & NEIGHBORS:\n" + "\n".join(rel_text_blocks) + "\n"
            driver.close()
        except Exception:
            pass
            
        # Deduplicate retrieved nodes
        unique_nodes = []
        seen_ids = set()
        for node in nodes_info:
            if node["id"] not in seen_ids:
                seen_ids.add(node["id"])
                unique_nodes.append(node)
        nodes_info = unique_nodes
        
        job_context = graph_context


    # --- TOKEN BUDGET MANAGER & TRIMMING LOGIC ---
    def estimate_tokens(txt: str) -> int:
        return len(txt) // 4
        
    core_system_prompt = """
    You are the 'SOP Compliance Assistant', an AI advisor integrated into a multi-agent SOP comparison platform.
    Your goal is to help users understand the results of scanning Global and Local SOPs, explain recommendations, 
    and answer questions regarding standard operating procedures, dynamic compliance labels, and the graph.
    
    === GROUNDING AND EVIDENCE GUARDRAILS ===
    - You must answer only using the retrieved graph context and active job context provided above.
    - If the user asks about active mismatches, compliance gaps, recommendations, or audit actions, you MUST base your answer EXCLUSIVELY on the compliance results (UI REPORT) provided. Do NOT count or list mismatches using the graph knowledge block.
    - Never write disclaimers like "these mismatches are based on the current graph context and may change". State mismatch facts directly as reported in the UI Report.
    - If the contexts provided are completely empty, or if they lack sufficient evidence to answer the user's question, you must explicitly state that the required knowledge is currently unavailable instead of hallucinating.
    - Do NOT make up any information.
    =========================================
    """
    
    # Prune mismatch details list if overall characters exceed limits
    context_chunks_used = len(detailed_recs)
    pruned_recs = list(detailed_recs)
    while len(str(pruned_recs)) > MAX_CONTEXT_CHARACTERS and pruned_recs:
        pruned_recs.pop() # Remove least relevant chunks first
        
    mismatches_context = ""
    if pruned_recs:
        mismatches_context += "\n- DETAILED COMPLIANCE MISMATCHES & AUDIT RECOMMENDATIONS (UI REPORT):\n"
        for idx, r in enumerate(pruned_recs):
            mismatches_context += f"  Mismatch {idx+1}: File: {r['file']}, Clause: {r['clause']}, Action: {r['action']}\n"
            mismatches_context += f"    Global text excerpt: \"{r['global']}\"\n"
            mismatches_context += f"    Local text excerpt: \"{r['local']}\"\n"
            mismatches_context += f"    Rationale: {r['rationale']}\n"

    dynamic_context = platform_metadata + "\n" + job_context + mismatches_context + graph_context
    full_prompt = core_system_prompt + "\n" + dynamic_context + "\nUser Question: " + message
    
    # Manage history token limits
    history_used = list(history)
    if len(history_used) > MAX_CHAT_HISTORY:
        history_used = history_used[-MAX_CHAT_HISTORY:] # Keep N most recent
        
    # Double check total token budget and trim recursively if needed
    trimming_occurred = False
    loop_limit = 10
    while loop_limit > 0:
        total_chars = len(full_prompt) + sum(len(m.get('content', '')) for m in history_used)
        total_tokens_est = estimate_tokens(full_prompt) + sum(estimate_tokens(m.get('content', '')) for m in history_used)
        
        if total_tokens_est <= (MODEL_TOKEN_LIMIT - TOKEN_SAFETY_MARGIN):
            break
            
        trimming_occurred = True
        if len(history_used) > 1:
            history_used.pop(0) # Trim oldest history exchange
        elif len(pruned_recs) > 1:
            pruned_recs.pop() # Trim more mismatch chunks
            # Update prompts
            mismatches_context = "\n- DETAILED COMPLIANCE MISMATCHES & AUDIT RECOMMENDATIONS (UI REPORT):\n"
            for idx, r in enumerate(pruned_recs):
                mismatches_context += f"  Mismatch {idx+1}: File: {r['file']}, Clause: {r['clause']}, Action: {r['action']}\n"
            dynamic_context = platform_metadata + "\n" + job_context + mismatches_context + graph_context
            full_prompt = core_system_prompt + "\n" + dynamic_context + "\nUser Question: " + message
        else:
            # Absolute fallback: clear graph context to save tokens
            graph_context = ""
            dynamic_context = platform_metadata + "\n" + job_context + mismatches_context
            full_prompt = core_system_prompt + "\n" + dynamic_context + "\nUser Question: " + message
            
        loop_limit -= 1

    final_token_count = estimate_tokens(full_prompt) + sum(estimate_tokens(m.get('content', '')) for m in history_used)

    # --- LOGGER OUTPUT ---
    print(f"[Chatbot Log] Retrieved Chunk Count: {context_chunks_used}")
    print(f"[Chatbot Log] Chat History Count: {len(history_used)}")
    print(f"[Chatbot Log] Trimming Occurred: {trimming_occurred}")
    print(f"[Chatbot Log] Final Estimated Tokens: {final_token_count}")
    
    system_prompt = core_system_prompt + "\n" + dynamic_context
    
    try:
        from llm.factory import LLMFactory
        chat_model = LLMFactory.get_chat_model()
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        messages = [SystemMessage(content=system_prompt)]
        
        # Build messages list
        for msg in history_used:
            role = msg.get('role')
            content = msg.get('content')
            if role == 'user':
                messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                messages.append(AIMessage(content=content))
                
        messages.append(HumanMessage(content=message))
        res = chat_model.invoke(messages)
        
        return jsonify({
            "success": True,
            "response": res.content.strip(),
            "nodes": nodes_info,
            "relationships": relationships_info
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        error_msg = str(e).lower()
        err_type = "API_ERROR"
        friendly_msg = "Sorry, I ran into an error connecting to the LLM assistant model. Please verify your settings."
        
        if "rate_limit" in error_msg or "rate limit" in error_msg or "429" in error_msg:
            err_type = "RATE_LIMIT"
            friendly_msg = "⚠️ The AI service has temporarily reached its usage limit. Please wait a few moments and try again."
        elif "token" in error_msg or "limit" in error_msg or "413" in error_msg:
            err_type = "TOKEN_LIMIT"
            friendly_msg = "⚠️ Your request is too large for the current AI model. Please shorten your question or start a new chat."
        elif "key" in error_msg or "auth" in error_msg or "api_key" in error_msg:
            err_type = "INVALID_KEY"
            friendly_msg = "⚠️ Unable to connect to the AI service because the configured API key is invalid."
        elif "quota" in error_msg or "billing" in error_msg or "insufficient" in error_msg:
            err_type = "QUOTA_EXCEEDED"
            friendly_msg = "⚠️ The configured AI API has reached its usage limit. Please update or recharge the existing API key in the application configuration."
        elif "connect" in error_msg or "timeout" in error_msg or "network" in error_msg:
            err_type = "NETWORK_ERROR"
            friendly_msg = "⚠️ Unable to reach the AI service. Please check your connection and try again."
            
        return jsonify({
            "success": False,
            "error_type": err_type,
            "message": friendly_msg
        })

@app.route('/api/graph/data', methods=['GET'])
def get_graph_data():
    from graph.writer import GraphWriter
    
    nodes = []
    links = []
    node_ids = set()
    
    try:
        writer = GraphWriter()
        writer.connect()
        driver = writer._driver
        
        with driver.session() as session:
            result = session.run("MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 150")
            for record in result:
                n = record.get("n")
                r = record.get("r")
                m = record.get("m")
                
                if n:
                    # Retrieve node ID safely
                    n_id = str(n.element_id) if hasattr(n, 'element_id') else str(n.id)
                    if n_id not in node_ids:
                        node_ids.add(n_id)
                        labels = list(n.labels)
                        label = labels[0] if labels else "Node"
                        props = dict(n)
                        name = props.get("name") or props.get("title") or props.get("number") or n_id
                        nodes.append({
                            "id": n_id,
                            "label": label,
                            "name": name,
                            "properties": props
                        })
                        
                if m:
                    m_id = str(m.element_id) if hasattr(m, 'element_id') else str(m.id)
                    if m_id not in node_ids:
                        node_ids.add(m_id)
                        labels = list(m.labels)
                        label = labels[0] if labels else "Node"
                        props = dict(m)
                        name = props.get("name") or props.get("title") or props.get("number") or m_id
                        nodes.append({
                            "id": m_id,
                            "label": label,
                            "name": name,
                            "properties": props
                        })
                        
                if r and n and m:
                    n_id = str(n.element_id) if hasattr(n, 'element_id') else str(n.id)
                    m_id = str(m.element_id) if hasattr(m, 'element_id') else str(m.id)
                    links.append({
                        "source": n_id,
                        "target": m_id,
                        "type": r.type
                    })
                    
        writer.close()
        return jsonify({
            "success": True,
            "nodes": nodes,
            "links": links,
            "source": "neo4j"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Neo4j offline: {str(e)}",
            "nodes": [],
            "links": [],
            "source": "fallback"
        })


@app.route('/api/health/neo4j', methods=['GET'])
def get_neo4j_health():
    from neo4j import GraphDatabase
    from config import config_instance
    try:
        driver = GraphDatabase.driver(
            config_instance.NEO4J_URI,
            auth=(config_instance.NEO4J_USER, config_instance.NEO4J_PASSWORD)
        )
        driver.verify_connectivity()
        driver.close()
        return jsonify({
            "status": "CONNECTED",
            "database": "Neo4j",
            "graph_available": True,
            "graphrag_available": True,
            "message": "Neo4j connection established successfully."
        })
    except Exception as e:
        return jsonify({
            "status": "OFFLINE",
            "database": "Neo4j",
            "graph_available": False,
            "graphrag_available": False,
            "message": f"Neo4j server is unavailable. GraphRAG features are disabled. Details: {str(e)}"
        })

@app.route('/api/sops', methods=['GET'])
def list_sops():
    """Lists all uploaded Global and Local SOP files."""
    try:
        global_files = []
        local_files = []
        
        if os.path.exists(GLOBAL_UPLOAD_DIR):
            for f in os.listdir(GLOBAL_UPLOAD_DIR):
                if f != '.gitkeep' and not f.startswith('.'):
                    path = os.path.join(GLOBAL_UPLOAD_DIR, f)
                    global_files.append({
                        "name": f,
                        "size_bytes": os.path.getsize(path),
                        "type": "global"
                    })
                    
        if os.path.exists(LOCAL_UPLOAD_DIR):
            for f in os.listdir(LOCAL_UPLOAD_DIR):
                if f != '.gitkeep' and not f.startswith('.'):
                    path = os.path.join(LOCAL_UPLOAD_DIR, f)
                    local_files.append({
                        "name": f,
                        "size_bytes": os.path.getsize(path),
                        "type": "local"
                    })
                    
        return jsonify({
            "success": True,
            "global": global_files,
            "local": local_files
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to list SOP files: {str(e)}"
        }), 500


@app.route('/api/sops/delete', methods=['POST'])
def delete_sops():
    """Deletes one or multiple SOPs from filesystem, job history, and Neo4j database."""
    import time
    start_time = time.time()
    
    data = request.json or {}
    sops_to_delete = data.get('sops', [])
    
    if not sops_to_delete:
        return jsonify({
            "success": False,
            "message": "No SOPs specified for deletion."
        }), 400
        
    from neo4j import GraphDatabase
    from config import config_instance
    
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
        print("Neo4j is offline, database deletion will be skipped.")
        
    deleted_count = 0
    deleted_nodes = 0
    deleted_rels = 0
    errors = []
    
    for sop in sops_to_delete:
        filename = sop.get('filename')
        sop_type = sop.get('type')
        
        if not filename or not sop_type:
            errors.append(f"Invalid SOP parameters: {sop}")
            continue
            
        # 1. Determine directory and paths
        folder = GLOBAL_UPLOAD_DIR if sop_type == 'global' else LOCAL_UPLOAD_DIR
        filepath = os.path.join(folder, filename)
        
        # 2. Delete file from storage
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"Deleted file: {filepath}")
            else:
                print(f"File not found on disk, proceeding with metadata cleanup: {filepath}")
        except Exception as fe:
            errors.append(f"Failed to delete file {filename}: {str(fe)}")
            continue
            
        # 3. Purge related comparison jobs
        jobs_to_remove = []
        for job_id, job in list(pipeline_jobs.items()):
            g_path = job.get("global_sop_path", "")
            l_paths = job.get("local_sop_paths", [])
            
            # Match paths (either absolute, relative, or just matching filename)
            match_global = (sop_type == 'global' and (g_path == filepath or os.path.basename(g_path) == filename))
            match_local = (sop_type == 'local' and any(lp == filepath or os.path.basename(lp) == filename for lp in l_paths))
            
            if match_global or match_local:
                jobs_to_remove.append(job_id)
                
        for jid in jobs_to_remove:
            pipeline_jobs.pop(jid, None)
            print(f"Purged comparison job: {jid}")
            
        if jobs_to_remove:
            save_jobs_to_disk()
            
        # 4. Neo4j Subgraph Deletion
        if neo4j_online and driver:
            try:
                with driver.session() as session:
                    # Fetch counts before deletion for audit logs
                    if sop_type == 'global':
                        count_query = """
                        MATCH (sop:SOP {id: 'global_sop'})
                        OPTIONAL MATCH (sop)-[:HAS_SECTION]->(sec:Section)
                        OPTIONAL MATCH (sec)-[:HAS_CLAUSE]->(c:Clause)
                        RETURN count(distinct sop) + count(distinct sec) + count(distinct c) as nodes
                        """
                        res = session.run(count_query)
                    else:
                        count_query = """
                        MATCH (sop:SOP)
                        WHERE sop.id = $filepath OR sop.id ENDS WITH $filename OR toLower(sop.name) = toLower($filename) OR toLower(sop.id) CONTAINS toLower($filename)
                        OPTIONAL MATCH (sop)-[:HAS_SECTION]->(sec:Section)
                        OPTIONAL MATCH (sec)-[:HAS_CLAUSE]->(c:Clause)
                        RETURN count(distinct sop) + count(distinct sec) + count(distinct c) as nodes
                        """
                        res = session.run(count_query, filepath=filepath, filename=filename)
                        
                    nodes_to_del = list(res)[0]["nodes"] if res else 0
                    
                    # Perform detach delete
                    if sop_type == 'global':
                        delete_query = """
                        MATCH (sop:SOP {id: 'global_sop'})
                        OPTIONAL MATCH (sop)-[:HAS_SECTION]->(sec:Section)
                        OPTIONAL MATCH (sec)-[:HAS_CLAUSE]->(c:Clause)
                        DETACH DELETE sop, sec, c
                        """
                        session.run(delete_query)
                    else:
                        delete_query = """
                        MATCH (sop:SOP)
                        WHERE sop.id = $filepath OR sop.id ENDS WITH $filename OR toLower(sop.name) = toLower($filename) OR toLower(sop.id) CONTAINS toLower($filename)
                        OPTIONAL MATCH (sop)-[:HAS_SECTION]->(sec:Section)
                        OPTIONAL MATCH (sec)-[:HAS_CLAUSE]->(c:Clause)
                        DETACH DELETE sop, sec, c
                        """
                        session.run(delete_query, filepath=filepath, filename=filename)
                        
                    deleted_nodes += nodes_to_del
                    
                    # Clean up orphaned custom entity nodes (PPE, Role, Equipment, etc.)
                    orphan_query = """
                    MATCH (n)
                    WHERE NOT n:SOP AND NOT n:Section AND NOT n:Clause AND NOT (n)--()
                    WITH n, count(n) as c
                    DELETE n
                    RETURN sum(c) as orphans_deleted
                    """
                    o_res = session.run(orphan_query)
                    records = list(o_res)
                    orphans_del = records[0]["orphans_deleted"] if records and records[0]["orphans_deleted"] is not None else 0
                    deleted_nodes += orphans_del
                    
                    print(f"Neo4j elements purged for {filename}. Nodes: {nodes_to_del}, Orphans: {orphans_del}")
            except Exception as ne:
                errors.append(f"Failed to delete Neo4j elements for {filename}: {str(ne)}")
                
        deleted_count += 1
        
    if driver:
        driver.close()
        
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Audit log entry
    status = "success" if not errors else "partial_success" if deleted_count > 0 else "failed"
    print(f"[AUDIT DELETE] SOP: {sops_to_delete} | Status: {status} | Nodes deleted: {deleted_nodes} | Duration: {duration_ms}ms | Errors: {errors}")
    
    return jsonify({
        "success": len(errors) == 0,
        "deleted_count": deleted_count,
        "nodes_deleted": deleted_nodes,
        "errors": errors,
        "duration_ms": duration_ms
    })
if __name__ == '__main__':
    port = config_instance.PORT
    print(f"Starting Multi-Agent SOP Comparison API on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=(config_instance.FLASK_ENV == 'development'))
