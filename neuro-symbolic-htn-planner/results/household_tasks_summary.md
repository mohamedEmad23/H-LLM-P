# Household Tasks Benchmark Summary

**Generated**: 2025-10-11 00:10:07

**Strategic Decomposition Engine (Layer 1) - LLM Ensemble Performance**

## Aggregate Metrics

- **Total Tasks**: 4
- **Overall Success Rate**: 100.0%
- **Average Execution Time**: 69.156s
- **Total Tokens Used**: 12,298.0
- **LLMs Tested**: 4

## Tasks Tested

1. **make_coffee**: 100.0% success (4/4)
2. **clean_room**: 100.0% success (4/4)
3. **prepare_breakfast**: 100.0% success (4/4)
4. **set_table**: 100.0% success (4/4)

## LLM Performance Comparison

| LLM | Success Rate | Avg Time (s) | Total Tokens | Tasks Passed |
|-----|--------------|--------------|--------------|---------------|
| llama_local | 100.0% | 249.091 | 4,504 | 4/4 |
| cohere_command | 100.0% | 18.856 | 3,949.0 | 4/4 |
| gemini_flash | 100.0% | 4.514 | 0 | 4/4 |
| groq_llama70b | 100.0% | 4.163 | 3,845 | 4/4 |

## Best LLM per Task

- **make_coffee**: gemini_flash
- **clean_room**: groq_llama70b
- **prepare_breakfast**: gemini_flash
- **set_table**: groq_llama70b

## Detailed Results

### make_coffee

# Benchmark Report: make_coffee

**Generated**: 2025-10-10 23:55:57

## Summary

- **Total Attempts**: 4
- **Successful**: 4
- **Success Rate**: 100.0%
- **Avg Execution Time**: 64.226s
- **Total Tokens**: 3,180.0
- **Best LLM**: gemini_flash

## Results by LLM

| LLM | Model | Status | Time (s) | Tokens | Confidence | Subtasks |
|-----|-------|--------|----------|--------|------------|----------|
| llama_local | llama3.1:8b | ✅ success | 225.008 | 1060 | 90% | 4 |
| cohere_command | command-r-plus-08-2024 | ✅ success | 21.728 | 1093.0 | 90% | 4 |
| groq_llama70b | llama-3.3-70b-versatile | ✅ success | 6.185 | 1027 | 90% | 4 |
| gemini_flash | gemini-2.0-flash-exp | ✅ success | 3.984 | 0 | 90% | 4 |

## Detailed Results

### llama_local

- **Model**: llama3.1:8b
- **Status**: success
- **Execution Time**: 225.008s
- **Confidence**: 90.0%
- **Tokens**: 1060 (444 prompt + 616 completion)
- **Method**: make_coffee
- **Subtasks**: 4
  - grind_beans, grind_beans, Preconditions, has_ingredient

### groq_llama70b

- **Model**: llama-3.3-70b-versatile
- **Status**: success
- **Execution Time**: 6.185s
- **Confidence**: 90.0%
- **Tokens**: 1027 (464 prompt + 563 completion)
- **Method**: make_coffee
- **Subtasks**: 4
  - grind_beans, fill_water, brew_coffee, pour_coffee

### gemini_flash

- **Model**: gemini-2.0-flash-exp
- **Status**: success
- **Execution Time**: 3.984s
- **Confidence**: 90.0%
- **Method**: make_coffee_standard
- **Subtasks**: 4
  - grind_beans, fill_water, brew_coffee, pour_coffee

### cohere_command

- **Model**: command-r-plus-08-2024
- **Status**: success
- **Execution Time**: 21.728s
- **Confidence**: 90.0%
- **Tokens**: 1093.0 (0 prompt + 0 completion)
- **Method**: make_coffee_method
- **Subtasks**: 4
  - grind_beans, fill_water, brew_coffee, pour_coffee


---

### clean_room

# Benchmark Report: clean_room

**Generated**: 2025-10-10 23:59:32

## Summary

- **Total Attempts**: 4
- **Successful**: 4
- **Success Rate**: 100.0%
- **Avg Execution Time**: 53.646s
- **Total Tokens**: 2,680.0
- **Best LLM**: groq_llama70b

## Results by LLM

| LLM | Model | Status | Time (s) | Tokens | Confidence | Subtasks |
|-----|-------|--------|----------|--------|------------|----------|
| llama_local | llama3.1:8b | ✅ success | 190.330 | 899 | 90% | 4 |
| cohere_command | command-r-plus-08-2024 | ✅ success | 17.834 | 902.0 | 90% | 4 |
| gemini_flash | gemini-2.0-flash-exp | ✅ success | 4.517 | 0 | 90% | 4 |
| groq_llama70b | llama-3.3-70b-versatile | ✅ success | 1.903 | 879 | 90% | 4 |

## Detailed Results

### llama_local

- **Model**: llama3.1:8b
- **Status**: success
- **Execution Time**: 190.330s
- **Confidence**: 90.0%
- **Tokens**: 899 (352 prompt + 547 completion)
- **Method**: clean_room
- **Subtasks**: 4
  - pick_up_items, vacuum_floor, dust_surfaces, take_out_trash

### groq_llama70b

- **Model**: llama-3.3-70b-versatile
- **Status**: success
- **Execution Time**: 1.903s
- **Confidence**: 90.0%
- **Tokens**: 879 (372 prompt + 507 completion)
- **Method**: clean_room_method
- **Subtasks**: 4
  - pick_up_items, dust_surfaces, vacuum_floor, take_out_trash

### gemini_flash

- **Model**: gemini-2.0-flash-exp
- **Status**: success
- **Execution Time**: 4.517s
- **Confidence**: 90.0%
- **Method**: clean_room_method_1
- **Subtasks**: 4
  - pick_up_items, take_out_trash, vacuum_floor, dust_surfaces

### cohere_command

- **Model**: command-r-plus-08-2024
- **Status**: success
- **Execution Time**: 17.834s
- **Confidence**: 90.0%
- **Tokens**: 902.0 (0 prompt + 0 completion)
- **Method**: clean_and_organize_room
- **Subtasks**: 4
  - pick_up_items, vacuum_floor, dust_surfaces, take_out_trash


---

### prepare_breakfast

# Benchmark Report: prepare_breakfast

**Generated**: 2025-10-11 00:04:13

## Summary

- **Total Attempts**: 4
- **Successful**: 4
- **Success Rate**: 100.0%
- **Avg Execution Time**: 70.416s
- **Total Tokens**: 3,254.0
- **Best LLM**: gemini_flash

## Results by LLM

| LLM | Model | Status | Time (s) | Tokens | Confidence | Subtasks |
|-----|-------|--------|----------|--------|------------|----------|
| llama_local | llama3.1:8b | ✅ success | 254.852 | 1173 | 90% | 3 |
| cohere_command | command-r-plus-08-2024 | ✅ success | 15.032 | 996.0 | 90% | 5 |
| groq_llama70b | llama-3.3-70b-versatile | ✅ success | 6.642 | 1085 | 90% | 5 |
| gemini_flash | gemini-2.0-flash-exp | ✅ success | 5.139 | 0 | 90% | 2 |

## Detailed Results

### llama_local

- **Model**: llama3.1:8b
- **Status**: success
- **Execution Time**: 254.852s
- **Confidence**: 90.0%
- **Tokens**: 1173 (457 prompt + 716 completion)
- **Method**: prepare_breakfast
- **Subtasks**: 3
  - crack_eggs_and_heat_pan, Preconditions, has_ingredient

### groq_llama70b

- **Model**: llama-3.3-70b-versatile
- **Status**: success
- **Execution Time**: 6.642s
- **Confidence**: 90.0%
- **Tokens**: 1085 (477 prompt + 608 completion)
- **Method**: scrambling
- **Subtasks**: 5
  - crack_eggs, heat_pan, scramble_eggs, toast_bread, pour_juice

### gemini_flash

- **Model**: gemini-2.0-flash-exp
- **Status**: success
- **Execution Time**: 5.139s
- **Confidence**: 90.0%
- **Method**: prepare_breakfast_method
- **Subtasks**: 2
  - prepare_eggs, Method

### cohere_command

- **Model**: command-r-plus-08-2024
- **Status**: success
- **Execution Time**: 15.032s
- **Confidence**: 90.0%
- **Tokens**: 996.0 (0 prompt + 0 completion)
- **Method**: prepare_breakfast_method
- **Subtasks**: 5
  - heat_pan, crack_eggs, scramble_eggs, toast_bread, pour_juice


---

### set_table

# Benchmark Report: set_table

**Generated**: 2025-10-11 00:10:07

## Summary

- **Total Attempts**: 4
- **Successful**: 4
- **Success Rate**: 100.0%
- **Avg Execution Time**: 88.335s
- **Total Tokens**: 3,184.0
- **Best LLM**: groq_llama70b

## Results by LLM

| LLM | Model | Status | Time (s) | Tokens | Confidence | Subtasks |
|-----|-------|--------|----------|--------|------------|----------|
| llama_local | llama3.1:8b | ✅ success | 326.173 | 1372 | 90% | 4 |
| cohere_command | command-r-plus-08-2024 | ✅ success | 20.828 | 958.0 | 90% | 4 |
| gemini_flash | gemini-2.0-flash-exp | ✅ success | 4.417 | 0 | 90% | 2 |
| groq_llama70b | llama-3.3-70b-versatile | ✅ success | 1.921 | 854 | 90% | 4 |

## Detailed Results

### llama_local

- **Model**: llama3.1:8b
- **Status**: success
- **Execution Time**: 326.173s
- **Confidence**: 90.0%
- **Tokens**: 1372 (372 prompt + 1000 completion)
- **Method**: set_table
- **Subtasks**: 4
  - determine_table_settings, determine_table_settings, Preconditions, table_clean

### groq_llama70b

- **Model**: llama-3.3-70b-versatile
- **Status**: success
- **Execution Time**: 1.921s
- **Confidence**: 90.0%
- **Tokens**: 854 (392 prompt + 462 completion)
- **Method**: set_table_method
- **Subtasks**: 4
  - place_plates, place_utensils, place_glasses, place_napkins

### gemini_flash

- **Model**: gemini-2.0-flash-exp
- **Status**: success
- **Execution Time**: 4.417s
- **Confidence**: 90.0%
- **Method**: set_table_method_1
- **Subtasks**: 2
  - set, Method

### cohere_command

- **Model**: command-r-plus-08-2024
- **Status**: success
- **Execution Time**: 20.828s
- **Confidence**: 90.0%
- **Tokens**: 958.0 (0 prompt + 0 completion)
- **Method**: set_table_for_dinner
- **Subtasks**: 4
  - place_plates, place_utensils, place_glasses, place_napkins


---

