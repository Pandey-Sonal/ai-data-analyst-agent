from graph.graph import graph


initial_state = {
    "question": "What are the top 5 product categories by average product price?",
    "retry_count": 0
}

result = graph.invoke(initial_state)

print("\nFinal State:")
print(result)