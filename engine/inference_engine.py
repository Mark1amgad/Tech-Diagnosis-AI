import json
from engine.confidence import ConfidenceSystem

class ForwardChainingEngine:
    def __init__(self, rules_path):
        with open(rules_path, 'r', encoding='utf-8') as f:
            self.rules = json.load(f)
            
    def infer(self, initial_facts_dict):
        """
        Multi-step forward chaining inference with loop protection.
        initial_facts_dict: { fact_id: {'value': bool, 'cf': float, 'name': str, 'is_inferred': False} }
        """
        memory = dict(initial_facts_dict) # Working memory of all facts
        
        trace_graph = [] # Edges representing fired rules
        fired_rules = set() # Loop protection memory: (rule_id, tuple_of_matched_facts)
        
        MAX_ITERATIONS = 100
        iteration = 0
        changed = True
        
        while changed and iteration < MAX_ITERATIONS:
            changed = False
            iteration += 1
            
            for rule in self.rules:
                rule_id = rule['id']
                conditions = rule['conditions']
                conclusion = rule['conclusion']
                rule_cf = rule.get('confidence', 1.0)
                priority = rule.get('priority', 0)
                layer = rule.get('layer', 'unknown')
                
                # Check if all conditions match in memory
                match = True
                condition_cfs = []
                matched_fact_ids = []
                
                for cond in conditions:
                    fact_id = cond['fact']
                    req_val = cond['value']
                    
                    if fact_id in memory and memory[fact_id]['value'] == req_val:
                        condition_cfs.append(memory[fact_id]['cf'])
                        matched_fact_ids.append(fact_id)
                    else:
                        match = False
                        break
                        
                if match:
                    # Loop Protection: Prevent redundant identical firing
                    firing_signature = (rule_id, tuple(sorted(matched_fact_ids)))
                    if firing_signature in fired_rules:
                        continue
                        
                    # Calculate new CF via Propagation
                    new_cf = ConfidenceSystem.propagate(rule_cf, condition_cfs)
                    conclusion_id = conclusion['fact']
                    
                    is_new_fact = conclusion_id not in memory
                    
                    if is_new_fact:
                        # Fact inferred for the first time
                        memory[conclusion_id] = {
                            'value': conclusion['value'],
                            'cf': new_cf,
                            'name': conclusion.get('name', conclusion_id),
                            'layer': layer,
                            'specificity': len(conditions),
                            'priority': priority,
                            'is_inferred': True
                        }
                        changed = True
                    else:
                        # Fact already exists, Combine Confidence
                        old_cf = memory[conclusion_id]['cf']
                        combined_cf = ConfidenceSystem.combine(old_cf, new_cf)
                        
                        # Only mark as changed if confidence increases meaningfully
                        if combined_cf - old_cf > 0.001:
                            memory[conclusion_id]['cf'] = combined_cf
                            # Update specificity if this path is stronger
                            if len(conditions) > memory[conclusion_id].get('specificity', 0):
                                memory[conclusion_id]['specificity'] = len(conditions)
                            changed = True
                            
                    # Record the trace graph edge
                    fired_rules.add(firing_signature)
                    trace_graph.append({
                        'rule_id': rule_id,
                        'from_facts': matched_fact_ids,
                        'to_fact': conclusion_id,
                        'layer': layer,
                        'cf_contribution': new_cf,
                        'rule_name': conclusion.get('name', conclusion_id)
                    })
                        
        return memory, trace_graph
