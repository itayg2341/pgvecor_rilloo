import os
import re
import json
from collections import defaultdict

def find_c_files(path):
    c_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(('.c', '.h')):
                c_files.append(os.path.join(root, file))
    return c_files

def parse_includes(filepath, project_headers):
    includes = []
    include_pattern = re.compile(r'#include\s+"([^"]+)"')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                match = include_pattern.match(line)
                if match:
                    header = match.group(1)
                    if header in project_headers:
                        includes.append(header)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return includes

def build_dependency_graph(files):
    graph = defaultdict(list)
    project_headers = {os.path.basename(f) for f in files if f.endswith('.h')}
    
    for f_path in files:
        f_name = os.path.basename(f_path)
        dependencies = parse_includes(f_path, project_headers)
        for dep in dependencies:
            graph[f_name].append(dep)
            
    return graph

def get_incoming_deps(graph):
    incoming = defaultdict(list)
    for node, deps in graph.items():
        for dep in deps:
            incoming[dep].append(node)
    return incoming

def find_sccs(graph):
    """Kosaraju's algorithm to find Strongly Connected Components"""
    visited = set()
    order = []
    
    nodes = list(graph.keys())
    # Add nodes that are only dependencies
    all_deps = set()
    for deps in graph.values():
        all_deps.update(deps)
    for dep in all_deps:
        if dep not in nodes:
            nodes.append(dep)

    def dfs1(node):
        if node not in visited:
            visited.add(node)
            for neighbor in graph.get(node, []):
                dfs1(neighbor)
            order.append(node)

    for node in nodes:
        if node not in visited:
            dfs1(node)
    
    # Transpose graph
    transposed_graph = defaultdict(list)
    for node, deps in graph.items():
        for dep in deps:
            transposed_graph[dep].append(node)

    visited.clear()
    sccs = []
    def dfs2(node, current_scc):
        if node not in visited:
            visited.add(node)
            current_scc.append(node)
            for neighbor in transposed_graph.get(node, []):
                dfs2(neighbor, current_scc)

    while order:
        node = order.pop()
        if node not in visited:
            scc = []
            dfs2(node, scc)
            sccs.append(scc)
            
    return [scc for scc in sccs if len(scc) > 0]


def main():
    src_path = 'src'
    c_files = find_c_files(src_path)
    
    # Get basenames for graph keys
    graph_files = [os.path.basename(f) for f in c_files]
    
    # Build graph with basenames
    outgoing_deps = build_dependency_graph(c_files)
    incoming_deps = get_incoming_deps(outgoing_deps)
    
    sccs = find_sccs(outgoing_deps)

    # Filter out single-element SCCs that are not part of a cycle
    cycles = [scc for scc in sccs if len(scc) > 1]
    
    # Create a condensed graph where SCCs are single nodes
    scc_map = {}
    for i, scc in enumerate(sccs):
        scc_name = "SCC_" + "_".join(sorted(scc))
        for node in scc:
            scc_map[node] = scc_name

    condensed_graph = defaultdict(set)
    condensed_incoming = defaultdict(set)
    
    for node, deps in outgoing_deps.items():
        node_scc = scc_map.get(node, node)
        for dep in deps:
            dep_scc = scc_map.get(dep, dep)
            if node_scc != dep_scc:
                condensed_graph[node_scc].add(dep_scc)
                condensed_incoming[dep_scc].add(node_scc)

    # Topological sort on the condensed graph
    order = []
    queue = [n for n, deps in condensed_incoming.items() if not deps]
    
    # Add nodes with no incoming or outgoing dependencies
    all_condensed_nodes = set(condensed_graph.keys()) | set(condensed_incoming.keys())
    for node in all_condensed_nodes:
        if not condensed_incoming.get(node) and node not in queue:
            queue.append(node)
            
    # Add nodes that are not in the condensed graph at all (no dependencies)
    all_graph_nodes = set(scc_map.values())
    for scc in sccs:
        scc_name = "SCC_" + "_".join(sorted(scc))
        if scc_name not in all_graph_nodes and len(scc) == 1:
             if not outgoing_deps.get(scc[0]) and not incoming_deps.get(scc[0]):
                if scc[0] not in queue:
                    queue.append(scc[0])


    # Adjust for nodes that have no outgoing dependencies but have incoming
    all_nodes_in_graph = set(outgoing_deps.keys()) | set(dep for deps in outgoing_deps.values() for dep in deps)
    isolated_nodes = [n for n in all_nodes_in_graph if not outgoing_deps.get(n) and not incoming_deps.get(n)]
    
    # Topological sort logic
    sorted_order = []
    
    # Start with nodes with no dependencies
    no_dep_nodes = [node for node in all_nodes_in_graph if not outgoing_deps.get(node)]
    
    # Kahn's algorithm for topological sort
    in_degree = {u: 0 for u in all_nodes_in_graph}
    for u in outgoing_deps:
        for v in outgoing_deps[u]:
            in_degree[v] += 1
            
    queue = [u for u in all_nodes_in_graph if in_degree[u] == 0]
    
    while queue:
        u = queue.pop(0)
        sorted_order.append(u)
        
        # Adjust for graph structure
        if u in outgoing_deps:
            for v in sorted(list(outgoing_deps[u])):
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

    # This gives a file-level ordering. Now group into stages.
    # A stage can contain all files with no outstanding dependencies.
    
    # We can use the reverse of the sorted order for migration
    migration_order = list(reversed(sorted_order))
    
    # Let's use a simpler approach for staging:
    # Stage 0: No dependencies
    # Stage 1: Depends only on Stage 0
    # etc.
    
    stages = []
    migrated = set()
    
    while len(migrated) < len(all_nodes_in_graph):
        current_stage = []
        for node in all_nodes_in_graph:
            if node not in migrated:
                deps = set(outgoing_deps.get(node, []))
                if deps.issubset(migrated):
                    current_stage.append(node)
        
        if not current_stage:
            # Handle cycles
            remaining_nodes = all_nodes_in_graph - migrated
            # Find a cycle and add it as a stage
            cycle_found = False
            for scc in sccs:
                scc_set = set(scc)
                if scc_set.issubset(remaining_nodes):
                    current_stage.extend(scc)
                    cycle_found = True
                    break
            if not cycle_found:
                 # Failsafe, add remaining nodes
                 current_stage.extend(list(remaining_nodes))


        stages.append(sorted(current_stage))
        for item in current_stage:
            migrated.add(item)

    # Prepare JSON output
    output = {
        "files": sorted(list(all_nodes_in_graph)),
        "dependencies": {k: sorted(v) for k, v in outgoing_deps.items()},
        "dependents": {k: sorted(v) for k, v in incoming_deps.items()},
        "cycles": [sorted(c) for c in cycles],
        "migration_plan": {
            f"stage_{i}": stage for i, stage in enumerate(stages)
        }
    }
    
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
