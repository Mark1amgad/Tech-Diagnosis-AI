class ExplanationSystem:
    def build_graph_explanation(self, memory, trace_graph, target_fact_id, depth=0):
        """
        Recursively builds an explanation trace by walking backward through
        the dependency graph from the target conclusion to the initial user facts.
        """
        if target_fact_id not in memory:
            return ""
            
        fact_data = memory[target_fact_id]
        indent = "  " * depth
        
        if not fact_data.get('is_inferred', False):
            return f"{indent}- {fact_data.get('name', target_fact_id)} (Initial User Input)"
            
        # Find all edges (rules) that concluded this fact
        contributing_edges = [e for e in trace_graph if e['to_fact'] == target_fact_id]
        
        lines = []
        lines.append(f"{indent}* Inferred: {fact_data.get('name', target_fact_id)} (Final CF: {fact_data['cf']:.2f})")
        
        for edge in contributing_edges:
            lines.append(f"{indent}  Because Rule {edge['rule_id']} fired:")
            for from_fact in edge['from_facts']:
                sub_exp = self.build_graph_explanation(memory, trace_graph, from_fact, depth + 2)
                if sub_exp:
                    lines.append(sub_exp)
                    
        return "\n".join(lines)
