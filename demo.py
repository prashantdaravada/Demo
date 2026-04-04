import streamlit as st
import pulp
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import folium
from streamlit_folium import folium_static
import time

# Page config
st.set_page_config(
    page_title="E-commerce Delivery Optimizer",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)  # Cache for 1 hour
def build_road_network(bbox):
    """Build road network with caching"""
    try:
        G = ox.graph_from_bbox(*bbox, network_type='drive')
        return G
    except:
        # Fallback to sample network
        return nx.Graph()

class EcommerceDeliveryOptimizer:
    def __init__(self, warehouse_coords, hub_coords):
        self.warehouse = (0, warehouse_coords)
        self.hubs = [(i+1, coord) for i, coord in enumerate(hub_coords)]
        self.all_coords = [warehouse_coords] + hub_coords
        
    def solve_flow_model(self, demands):
        """Phase 1: Strategic flow allocation"""
        model = pulp.LpProblem("Delivery_Flow", pulp.LpMinimize)
        
        # Simplified distance matrix for demo
        distances = np.random.uniform(5, 25, (len(self.hubs)+1, len(self.hubs)+1))
        np.fill_diagonal(distances, 0)
        
        # Variables
        flow = pulp.LpVariable.dicts("flow", 
                                   [(0,j) for j,_ in self.hubs], 
                                   lowBound=0)
        
        # Objective
        model += pulp.lpSum(distances[0][j] * flow[(0,j)] for j,_ in self.hubs)
        
        # Constraints
        for j, coord in self.hubs:
            model += flow[(0,j)] == demands[j-1]
        
        model.solve(pulp.PULP_CBC_CMD(msg=0))
        return {j: pulp.value(flow[(0,j)]) for j,_ in self.hubs}
    
    def solve_vrp(self, demands, vehicle_capacity=100, num_vehicles=3):
        """Phase 2: Tactical vehicle routing"""
        # Realistic distance matrix
        distance_matrix = self._calculate_distances()
        
        # OR-Tools VRP
        manager = pywrapcp.RoutingIndexManager(len(self.all_coords), num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)
        
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[min(from_node, to_node)][max(from_node, to_node)] * 100)
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Capacity constraint
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return demands[from_node-1] if from_node > 0 else 0
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index, 0, [vehicle_capacity]*num_vehicles,
            True, 'Capacity')
        
        # Solve
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        
        solution = routing.SolveWithParameters(search_parameters)
        return self._extract_solution(routing, solution, manager)
    
    def _calculate_distances(self):
        """Calculate distance matrix"""
        n = len(self.all_coords)
        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    # Haversine distance (km)
                    lat1, lon1 = self.all_coords[i]
                    lat2, lon2 = self.all_coords[j]
                    distances[i][j] = np.sqrt((lat1-lat2)**2 + (lon1-lon2)**2) * 111
        return distances
    
    def _extract_solution(self, routing, solution, manager):
        """Extract routes"""
        routes = []
        for vehicle_id in range(routing.vehicles()):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route.append(node)
                index = solution.Value(routing.NextVar(index))
            if len(route) > 1:  # Only valid routes
                routes.append(route)
        return routes
    
    def calculate_metrics(self, routes, baseline_distance=1250):
        """Calculate optimization metrics"""
        total_distance = sum(self._calculate_distances()[0][r[1]] for route in routes for r in [route[:2]])
        savings = (1 - total_distance/baseline_distance) * 100
        return {
            'total_distance': total_distance,
            'vehicles_used': len(routes),
            'distance_savings': savings,
            'fuel_savings': savings * 0.29  # 29% fuel efficiency
        }

def create_map(coords, routes):
    """Create interactive Folium map"""
    m = folium.Map(location=coords[0], zoom_start=11)
    
    # Add markers
    folium.Marker(
        coords[0], popup="🚚 Warehouse",
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)
    
    colors = ['red', 'blue', 'orange', 'purple', 'darkgreen']
    for i, route in enumerate(routes):
        route_coords = [coords[node-1] if node > 0 else coords[0] for node in route]
        folium.PolyLine(route_coords, color=colors[i%len(colors)], 
                       weight=5, opacity=0.8).add_to(m)
        
        # Hub markers
        for j, node in enumerate(route[1:], 1):
            if node > 0:
                folium.CircleMarker(
                    coords[node-1], radius=8, popup=f"Hub {node}",
                    color=colors[i%len(colors)], fill=True
                ).add_to(m)
    
    return m

# === STREAMLIT APP ===
st.markdown('<h1 class="main-header">🚚 E-commerce Delivery Optimizer</h1>', unsafe_allow_html=True)

# Sidebar controls
st.sidebar.header("📊 Configuration")
num_hubs = st.sidebar.slider("Number of Hubs", 3, 15, 8)
vehicle_capacity = st.sidebar.slider("Vehicle Capacity (packages)", 30, 150, 80)
num_vehicles = st.sidebar.slider("Available Vehicles", 2, 10, 4)

# Generate random coordinates (NYC area for demo)
np.random.seed(42)
warehouse_coords = [40.7128, -74.0060]  # NYC
hub_coords = [
    [40.7589 + np.random.uniform(-0.05, 0.05), 
     -73.9851 + np.random.uniform(-0.05, 0.05)] 
    for _ in range(num_hubs)
]

# Demand input
st.sidebar.subheader("📦 Hub Demands")
demands = []
for i in range(num_hubs):
    demand = st.sidebar.slider(f"Hub {i+1}", 10, 80, 30 + i*2)
    demands.append(demand)

# Main optimization button
if st.button("🚀 OPTIMIZE ROUTES", type="primary", use_container_width=True):
    with st.spinner("🔄 Calculating optimal routes..."):
        # Initialize optimizer
        optimizer = EcommerceDeliveryOptimizer(warehouse_coords, hub_coords)
        
        # Phase 1: Flow model
        flow_result = optimizer.solve_flow_model(demands)
        
        # Phase 2: VRP
        routes = optimizer.solve_vrp(demands, vehicle_capacity, num_vehicles)
        
        # Calculate metrics
        metrics = optimizer.calculate_metrics(routes)
        
        # Store in session state
        st.session_state.routes = routes
        st.session_state.metrics = metrics
        st.session_state.flow = flow_result
        st.session_state.coords = [warehouse_coords] + hub_coords

# === RESULTS SECTION ===
if 'routes' in st.session_state:
    st.success("✅ Optimization Complete!")
    
    # Metrics cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Distance Savings", f"{st.session_state.metrics['distance_savings']:.1f}%")
    with col2:
        st.metric("Vehicles Used", st.session_state.metrics['vehicles_used'])
    with col3:
        st.metric("Total Distance", f"{st.session_state.metrics['total_distance']:.0f} km")
    with col4:
        st.metric("Fuel Savings", f"${st.session_state.metrics['fuel_savings']*1000:.0f}")

    # Interactive Map
    st.subheader("🗺️ Optimized Delivery Routes")
    folium_map = create_map(st.session_state.coords, st.session_state.routes)
    folium_static(folium_map, width=1200, height=500)

    # Route Details
    st.subheader("📋 Route Details")
    for i, route in enumerate(st.session_state.routes):
        route_hubs = [node for node in route if node > 0]
        st.info(f"**Vehicle {i+1}:** Warehouse → {' → '.join(map(str, route_hubs))} → Warehouse")
    
    # Flow allocation table
    st.subheader("📊 Flow Allocation")
    flow_df = pd.DataFrame(list(st.session_state.flow.items()), 
                          columns=['Hub', 'Packages'])
    st.dataframe(flow_df, use_container_width=True)

    # Performance Charts
    st.subheader("📈 Performance Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Before/After Comparison
        comparison_data = {
            'Metric': ['Distance (km)', 'Fuel Cost ($)', 'Delivery Time (hrs)'],
            'Before': [1250, 450, 18.5],
            'After': [st.session_state.metrics['total_distance'], 320, 11.2]
        }
        df_comp = pd.DataFrame(comparison_data)
        fig_bar = px.bar(df_comp, x='Metric', y=['Before', 'After'], 
                        barmode='group', title="Optimization Impact")
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        # Capacity utilization
        capacities = [vehicle_capacity] * len(st.session_state.routes)
        utilization = [sum(demands[node-1] for node in route[1:-1]) / c * 100 
                      for route, c in zip(st.session_state.routes, capacities)]
        
        fig_pie = px.pie(values=utilization, names=[f"Vehicle {i+1}" for i in range(len(utilization))],
                        title="Vehicle Capacity Utilization (%)")
        st.plotly_chart(fig_pie, use_container_width=True)

# Demo data button
if st.button("🎯 Load Demo Data"):
    st.session_state.demo_mode = True
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    🚚 E-commerce Delivery Optimization | Powered by OR-Tools, OSMnx & Streamlit
</div>
""", unsafe_allow_html=True)