import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt

# Try importing Louvain
try:
    from community import community_louvain
except ImportError:
    st.error("Please install: pip install python-louvain")
    st.stop()

# -----------------------------------
# Page Config
# -----------------------------------
st.set_page_config(page_title="Fan Network Analysis", layout="wide")

st.title("🎬 Entertainment Fan Network Analysis")

st.markdown("Analyze fan communities and identify influencers using Graph Theory.")

# -----------------------------------
# User Input Section
# -----------------------------------
st.sidebar.header("🔧 Input Network")

st.sidebar.markdown("Enter edges (connections) as comma-separated pairs:")
st.sidebar.markdown("Example: A-B, B-C, C-D")

edge_input = st.sidebar.text_area(
    "Enter Connections",
    "A-B, A-D, B-D, B-E, C-E, C-F, E-F"
)

# -----------------------------------
# Parse Input
# -----------------------------------
def parse_edges(edge_text):
    edges = []
    pairs = edge_text.split(",")
    for pair in pairs:
        if "-" in pair:
            u, v = pair.strip().split("-")
            edges.append((u.strip(), v.strip()))
    return edges


# -----------------------------------
# Analysis Function
# -----------------------------------
def run_analysis(edges):
    G = nx.Graph()
    G.add_edges_from(edges)

    # Community Detection
    partition = community_louvain.best_partition(G)

    # Influencer Ranking
    pagerank = nx.pagerank(G)
    degree = nx.degree_centrality(G)

    sorted_pr = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)

    return G, partition, sorted_pr, degree


# -----------------------------------
# Visualization Function
# -----------------------------------
def draw_graph(G, partition):
    pos = nx.spring_layout(G, seed=42)
    colors = [partition[node] for node in G.nodes()]

    fig, ax = plt.subplots()
    nx.draw(
        G, pos,
        with_labels=True,
        node_color=colors,
        cmap=plt.cm.Set3,
        node_size=800,
        font_size=10,
        ax=ax
    )
    return fig


# -----------------------------------
# Run Analysis Button
# -----------------------------------
if st.button("Run Analysis"):

    edges = parse_edges(edge_input)

    if len(edges) == 0:
        st.warning("Please enter valid edges!")
    else:
        G, partition, influencers, degree = run_analysis(edges)

        col1, col2 = st.columns(2)

        # -------------------------------
        # Graph Visualization
        # -------------------------------
        with col1:
            st.subheader("📊 Network Graph")
            fig = draw_graph(G, partition)
            st.pyplot(fig)

        # -------------------------------
        # Results
        # -------------------------------
        with col2:
            st.subheader("⭐ Influencer Ranking (PageRank)")
            for node, score in influencers:
                st.write(f"{node}: {round(score, 3)}")

            st.subheader("📈 Degree Centrality")
            for node, score in degree.items():
                st.write(f"{node}: {round(score, 3)}")

        # -------------------------------
        # Communities
        # -------------------------------
        st.subheader("👥 Detected Communities")

        community_dict = {}
        for node, comm in partition.items():
            community_dict.setdefault(comm, []).append(node)

        for comm, members in community_dict.items():
            st.write(f"Community {comm}: {members}")
