import os
import json
from engine.inference_engine import ForwardChainingEngine
from engine.explanation import ExplanationSystem

def run_test():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    facts_path = os.path.join(base_dir, 'knowledge_base', 'facts.json')
    rules_path = os.path.join(base_dir, 'knowledge_base', 'rules.json')
    
    engine = ForwardChainingEngine(rules_path)
    explainer = ExplanationSystem()
    
    # Simulate user input: Overheating, Fan Noise High, Device Old
    initial_facts = {
        'overheating': {'value': True, 'cf': 1.0, 'name': 'Device feels unusually hot', 'is_inferred': False},
        'fan_noise_high': {'value': True, 'cf': 1.0, 'name': 'Fans are loud or constantly spinning', 'is_inferred': False},
        'device_old': {'value': True, 'cf': 1.0, 'name': 'Device is more than 4 years old', 'is_inferred': False}
    }
    
    memory, trace_graph = engine.infer(initial_facts)
    
    print("=== MULTI-STEP REASONING TEST ===")
    for fact_id, data in memory.items():
        if data.get('is_inferred', False) and data.get('layer') == 'recommendation':
            print(f"\nTarget Recommendation: {data['name']} (CF: {data['cf']:.2f})")
            print(explainer.build_graph_explanation(memory, trace_graph, fact_id))
            
if __name__ == "__main__":
    run_test()
