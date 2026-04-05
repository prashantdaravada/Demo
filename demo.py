import streamlit as st
import heapq

# --------------------------------------------------
# FLOW ALLOCATION
# --------------------------------------------------
def allocate_flow(supply, hub_demands):
    allocation = {}
    remaining = supply

    for hub, demand in hub_demands.items():
        allocated = min(demand, remaining)
        allocation[hub] = allocated
        remaining -= allocated

    return allocation


# --------------------------------------------------
# DIJKSTRA ALGORITHM
# --------------------------------------------------
def dijkstra(graph, start):
    distances = {node: float('inf') for node in graph}
    distances[start] = 0

    pq = [(0, start)]

    while pq:
        current_dist, current_node = heapq.heappop(pq)

        for neighbor, weight in graph[current_node]:
            distance = current_dist + weight

            if distance < distances[neighbor]:
                distances[neighbor] = distance
                heapq.heappush(pq, (distance, neighbor))

    return distances


# --------------------------------------------------
# SAMPLE GRAPH
# --------------------------------------------------
graph = {
    'HubA': [('C1', 4), ('C2', 6), ('C3', 5)],
    'HubB': [('C4', 3), ('C5', 7), ('C6', 4)],
    'C1': [], 'C2': [], 'C3': [],
    'C4': [], 'C5': [], 'C6': []
}


# --------------------------------------------------
# STREAMLIT UI
# --------------------------------------------------
st.title("🚚 E-commerce Delivery Optimization")

st.sidebar.header("Input Parameters")

# User Inputs
supply = st.sidebar.number_input("Warehouse Supply", min_value=0, value=100)

hubA_demand = st.sidebar.number_input("HubA Demand", min_value=0, value=60)
hubB_demand = st.sidebar.number_input("HubB Demand", min_value=0, value=50)

hub_demands = {
    'HubA': hubA_demand,
    'HubB': hubB_demand
}


# --------------------------------------------------
# RUN BUTTON
# --------------------------------------------------
if st.sidebar.button("Optimize Delivery"):

    # Flow Optimization
    st.subheader("📦 Flow Allocation (Warehouse → Hubs)")
    flow = allocate_flow(supply, hub_demands)

    for hub, qty in flow.items():
        st.write(f"{hub}: {qty} packages")

    # Routing Optimization
    st.subheader("🗺️ Routing (Shortest Paths)")

    for hub in hub_demands.keys():
        distances = dijkstra(graph, hub)

        st.write(f"**From {hub}:**")
        for node, dist in distances.items():
            if node.startswith('C'):
                st.write(f"{hub} → {node} = {dist}")
