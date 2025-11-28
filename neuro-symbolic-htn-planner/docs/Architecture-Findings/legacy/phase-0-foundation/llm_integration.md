# Practical Framework for Implementing an HTN Planner Using LLMs

## Tools and Technologies

### 1. Programming Language
- **Python**: A versatile language with extensive libraries for AI and planning.

### 2. HTN Planning Frameworks
- **PyHop**: A lightweight HTN planner that is easy to use and modify. It is open-source and suitable for educational purposes.
- **SHOP2**: Another HTN planner that is more advanced and can handle more complex planning tasks. It is also open-source.

### 3. Large Language Models (LLMs)
- **Hugging Face Transformers**: Use pre-trained models available for free. Models like GPT-2 or DistilGPT-2 can be fine-tuned for specific tasks without incurring costs.
- **OpenAI GPT-3**: If you need access to a more powerful model, consider using the OpenAI API, but note that it requires payment.

### 4. Natural Language Processing Libraries
- **spaCy**: A free library for advanced NLP tasks, useful for parsing and understanding natural language inputs.
- **NLTK**: Another free library for NLP that can be used for simpler tasks.

### 5. Data Storage
- **SQLite**: A lightweight, serverless database that can be used to store planning data and results.
- **JSON Files**: For simple data storage, you can use JSON files to save and load task definitions and planning results.

### 6. Development Environment
- **Jupyter Notebook**: Ideal for prototyping and testing your HTN planner interactively.
- **VS Code**: A powerful code editor that supports Python development with extensions.

### 7. Testing Framework
- **pytest**: A free testing framework for Python that can be used to write unit tests for your planner.

### 8. Visualization Tools
- **Matplotlib**: A plotting library for Python that can be used to visualize planning processes and results.
- **Graphviz**: A tool for creating visual representations of task networks.

### 9. Documentation
- **Sphinx**: A free tool for generating documentation from your code, useful for maintaining clear project documentation.

## Implementation Steps

1. **Set Up the Environment**: Install Python and set up a virtual environment. Install necessary libraries using pip:
   - pip install pyhop
   - pip install spacy
   - pip install nltk
   - pip install matplotlib
   - pip install pytest
   - pip install sphinx

2. **Define the HTN Planner**: Use PyHop or SHOP2 to create the core HTN planning functionality. Define operators and methods for your specific domain.

3. **Integrate LLMs**: Use Hugging Face Transformers to load a pre-trained model. Implement the LLM query mechanism to generate task decompositions.

4. **Implement the Knowledge Gap Detector**: Create a mechanism to identify when the planner needs to query the LLM for additional information.

5. **Create the Verifier Task Mechanism**: Implement the logic to verify the outputs from the LLM using the symbolic planner's capabilities.

6. **Testing and Validation**: Use pytest to write tests for your planner, ensuring that it behaves as expected.

7. **Documentation**: Use Sphinx to document your code and provide usage examples.

## Optional Paid Tools (Low Priority)
- **OpenAI API**: For access to GPT-3 or other advanced models, consider using the OpenAI API, which requires payment for API keys.

This framework provides a comprehensive starting point for implementing an HTN planner using LLMs, focusing on free and open-source tools wherever possible.
