"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: gpt_structure.py
Description: Wrapper functions for calling OpenAI APIs.
"""
import json
import random
import time
import os

from openai import OpenAI
from utils import *

_CHAT_MODEL = "gpt-4o-mini"
_INSTRUCT_MODEL = "gpt-3.5-turbo-instruct"  # legacy completions endpoint — supports stop sequences
_EMBEDDING_MODEL = "text-embedding-ada-002"

_embedding_client = OpenAI(api_key=openai_api_key, timeout=30.0)
_completion_client = OpenAI(api_key=openai_api_key, timeout=30.0)
_instruct_client = OpenAI(api_key=openai_api_key, timeout=30.0)

# ---------------------------------------------------------------------------
# Token usage tracker
# All LLM calls go through this module, so we track everything here.
# Call get_token_summary() at any point to see cumulative usage.
# ---------------------------------------------------------------------------
_token_log = []  # list of dicts, one per API call

def _record_usage(call_type, prompt_tokens, completion_tokens, caller=None):
  _token_log.append({
    "call_type": call_type,
    "prompt_tokens": prompt_tokens,
    "completion_tokens": completion_tokens,
    "total_tokens": prompt_tokens + completion_tokens,
    "caller": caller,
    "timestamp": time.time(),
  })

def get_token_summary():
  total_prompt = sum(e["prompt_tokens"] for e in _token_log)
  total_completion = sum(e["completion_tokens"] for e in _token_log)
  total = total_prompt + total_completion
  n_calls = len(_token_log)
  # gpt-4o-mini pricing (as of 2024): $0.15/1M input, $0.60/1M output
  cost_usd = (total_prompt * 0.15 + total_completion * 0.60) / 1_000_000
  print(f"[TOKEN USAGE] calls={n_calls} | prompt={total_prompt:,} | "
        f"completion={total_completion:,} | total={total:,} | "
        f"est. cost=${cost_usd:.4f}")
  return {"calls": n_calls, "prompt_tokens": total_prompt,
          "completion_tokens": total_completion, "total_tokens": total,
          "estimated_cost_usd": cost_usd}

def save_token_log(filepath):
  """Save full per-call token log to a JSON file for evaluation analysis."""
  os.makedirs(os.path.dirname(filepath), exist_ok=True)
  with open(filepath, "w") as f:
    json.dump({"summary": get_token_summary(), "calls": _token_log}, f, indent=2)
  print(f"[TOKEN USAGE] Log saved to {filepath}")

def temp_sleep(seconds=0.1):
  time.sleep(seconds)

def ChatGPT_single_request(prompt):
  temp_sleep()
  for attempt in range(3):
    try:
      completion = _completion_client.chat.completions.create(
        model=_CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}]
      )
      return completion.choices[0].message.content
    except Exception as e:
      print(f"ChatGPT_single_request ERROR (attempt {attempt+1}/3): {e}")
      if attempt < 2:
        time.sleep(2 ** attempt)
  return ""


# ============================================================================
# #####################[SECTION 1: CHATGPT-3 STRUCTURE] ######################
# ============================================================================

def GPT4_request(prompt):
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response.
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of
                   the parameter and the values indicating the parameter
                   values.
  RETURNS:
    a str of GPT-3's response.
  """
  temp_sleep()

  try:
    response = _completion_client.chat.completions.create(
        model=_CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    _record_usage("GPT4_request", response.usage.prompt_tokens,
                  response.usage.completion_tokens)
    return response.choices[0].message.content

  except Exception as e:
    print("ChatGPT ERROR:", getattr(e, "message", str(e)))
    return "ChatGPT ERROR"


def ChatGPT_request(prompt):
  """
  Given a prompt and a dictionary of GPT parameters, make a request to the
  xAI server and returns the response.
  """
  import re as _re
  for attempt in range(5):
    try:
      response = _completion_client.chat.completions.create(
          model=_CHAT_MODEL,
          messages=[{"role": "user", "content": prompt}]
      )
      _record_usage("ChatGPT_request", response.usage.prompt_tokens,
                    response.usage.completion_tokens)
      return response.choices[0].message.content

    except Exception as e:
      err_msg = str(getattr(e, "message", str(e)))
      print(f"ChatGPT ERROR (attempt {attempt+1}/5):", err_msg)
      if attempt < 4:
        wait = 2.0
        m = _re.search(r'try again in (\d+)ms', err_msg)
        if m:
          wait = int(m.group(1)) / 1000.0 + 0.1
        wait += random.uniform(0, 1.0)
        time.sleep(wait)
  return "ChatGPT ERROR"


def GPT4_safe_generate_response(prompt, 
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False): 
  prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
  prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
  prompt += "Example output json:\n"
  prompt += '{"output": "' + str(example_output) + '"}'

  if verbose: 
    print ("CHAT GPT PROMPT")
    print (prompt)

  for i in range(repeat): 

    try: 
      curr_gpt_response = GPT4_request(prompt).strip()
      end_index = curr_gpt_response.rfind('}') + 1
      curr_gpt_response = curr_gpt_response[:end_index]
      curr_gpt_response = json.loads(curr_gpt_response)["output"]
      
      if func_validate(curr_gpt_response, prompt=prompt): 
        return func_clean_up(curr_gpt_response, prompt=prompt)
      
      if verbose: 
        print ("---- repeat count: \n", i, curr_gpt_response)
        print (curr_gpt_response)
        print ("~~~~")

    except: 
      pass

  return False


def ChatGPT_safe_generate_response(prompt, 
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False): 
  # prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
  prompt = '"""\n' + prompt + '\n"""\n'
  prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
  prompt += "Example output json:\n"
  prompt += '{"output": "' + str(example_output) + '"}'

  if verbose: 
    print ("CHAT GPT PROMPT")
    print (prompt)

  for i in range(repeat): 

    try: 
      curr_gpt_response = ChatGPT_request(prompt).strip()
      end_index = curr_gpt_response.rfind('}') + 1
      curr_gpt_response = curr_gpt_response[:end_index]
      curr_gpt_response = json.loads(curr_gpt_response)["output"]

      # print ("---ashdfaf")
      # print (curr_gpt_response)
      # print ("000asdfhia")
      
      if func_validate(curr_gpt_response, prompt=prompt): 
        return func_clean_up(curr_gpt_response, prompt=prompt)
      
      if verbose: 
        print ("---- repeat count: \n", i, curr_gpt_response)
        print (curr_gpt_response)
        print ("~~~~")

    except: 
      pass

  return False


def ChatGPT_safe_generate_response_OLD(prompt, 
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False): 
  if verbose: 
    print ("CHAT GPT PROMPT")
    print (prompt)

  for i in range(repeat): 
    try: 
      curr_gpt_response = ChatGPT_request(prompt).strip()
      if func_validate(curr_gpt_response, prompt=prompt): 
        return func_clean_up(curr_gpt_response, prompt=prompt)
      if verbose: 
        print (f"---- repeat count: {i}")
        print (curr_gpt_response)
        print ("~~~~")

    except: 
      pass
  print ("FAIL SAFE TRIGGERED") 
  return fail_safe_response


# ============================================================================
# ###################[SECTION 2: ORIGINAL GPT-3 STRUCTURE] ###################
# ============================================================================

def GPT_request(prompt, gpt_parameter): 
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response. 
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of  
                   the parameter and the values indicating the parameter 
                   values.   
  RETURNS: 
    a str of GPT-3's response. 
  """
  temp_sleep()
  for attempt in range(6):
    try:
      # Use the legacy completions endpoint so stop sequences are honoured.
      # gpt-3.5-turbo-instruct is the current replacement for text-davinci-003.
      response = _instruct_client.completions.create(
          model=_INSTRUCT_MODEL,
          prompt=prompt,
          temperature=gpt_parameter["temperature"],
          max_tokens=gpt_parameter["max_tokens"],
          top_p=gpt_parameter["top_p"],
          frequency_penalty=gpt_parameter["frequency_penalty"],
          presence_penalty=gpt_parameter["presence_penalty"],
          stop=gpt_parameter.get("stop"),
      )
      _record_usage("GPT_request", response.usage.prompt_tokens,
                    response.usage.completion_tokens)
      return response.choices[0].text
    except Exception as e:
      err_msg = str(getattr(e, "message", str(e)))
      print(f"GPT_request error (attempt {attempt+1}/6): {type(e).__name__}: {err_msg}")
      if attempt < 5:
        # Parse retry-after from error message if present (e.g. "try again in 711ms")
        wait = 2.0
        import re as _re
        m = _re.search(r'try again in (\d+)ms', err_msg)
        if m:
          wait = int(m.group(1)) / 1000.0 + 0.1
        # Add random jitter to desynchronize parallel threads
        wait += random.uniform(0, 1.0)
        time.sleep(wait)
  return ""  # empty string — callers use fail_safe, never store this in schedules


def generate_prompt(curr_input, prompt_lib_file): 
  """
  Takes in the current input (e.g. comment that you want to classifiy) and 
  the path to a prompt file. The prompt file contains the raw str prompt that
  will be used, which contains the following substr: !<INPUT>! -- this 
  function replaces this substr with the actual curr_input to produce the 
  final promopt that will be sent to the GPT3 server. 
  ARGS:
    curr_input: the input we want to feed in (IF THERE ARE MORE THAN ONE
                INPUT, THIS CAN BE A LIST.)
    prompt_lib_file: the path to the promopt file. 
  RETURNS: 
    a str prompt that will be sent to OpenAI's GPT server.  
  """
  if type(curr_input) == type("string"): 
    curr_input = [curr_input]
  curr_input = [str(i) for i in curr_input]

  f = open(prompt_lib_file, "r")
  prompt = f.read()
  f.close()
  for count, i in enumerate(curr_input):   
    prompt = prompt.replace(f"!<INPUT {count}>!", i)
  if "<commentblockmarker>###</commentblockmarker>" in prompt: 
    prompt = prompt.split("<commentblockmarker>###</commentblockmarker>")[1]
  return prompt.strip()


def safe_generate_response(prompt, 
                           gpt_parameter,
                           repeat=5,
                           fail_safe_response="error",
                           func_validate=None,
                           func_clean_up=None,
                           verbose=False): 
  if verbose: 
    print (prompt)

  for i in range(repeat): 
    curr_gpt_response = GPT_request(prompt, gpt_parameter)
    if func_validate(curr_gpt_response, prompt=prompt): 
      return func_clean_up(curr_gpt_response, prompt=prompt)
    if verbose: 
      print ("---- repeat count: ", i, curr_gpt_response)
      print (curr_gpt_response)
      print ("~~~~")
  return fail_safe_response


def get_embedding(text, model=_EMBEDDING_MODEL):
  text = text.replace("\n", " ")
  if not text:
    text = "this is blank"
  for attempt in range(3):
    try:
      response = _embedding_client.embeddings.create(input=[text], model=model)
      return response.data[0].embedding
    except Exception as e:
      print(f"get_embedding ERROR (attempt {attempt+1}/3): {e}")
      if attempt < 2:
        time.sleep(2 ** attempt)
  return [0] * 1536  # fallback: zero vector (ada-002 dimension)


if __name__ == '__main__':
  gpt_parameter = {"engine": "text-davinci-003", "max_tokens": 50, 
                   "temperature": 0, "top_p": 1, "stream": False,
                   "frequency_penalty": 0, "presence_penalty": 0, 
                   "stop": ['"']}
  curr_input = ["driving to a friend's house"]
  prompt_lib_file = "prompt_template/test_prompt_July5.txt"
  prompt = generate_prompt(curr_input, prompt_lib_file)

  def __func_validate(gpt_response): 
    if len(gpt_response.strip()) <= 1:
      return False
    if len(gpt_response.strip().split(" ")) > 1: 
      return False
    return True
  def __func_clean_up(gpt_response):
    cleaned_response = gpt_response.strip()
    return cleaned_response

  output = safe_generate_response(prompt, 
                                 gpt_parameter,
                                 5,
                                 "rest",
                                 __func_validate,
                                 __func_clean_up,
                                 True)

  print (output)




















