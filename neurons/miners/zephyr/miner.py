# The MIT License (MIT)
# Copyright © 2023 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import time
import torch
import typing
import argparse
import bittensor as bt

# Bittensor Miner Template:
import prompting
from prompting.protocol import PromptingSynapse
from prompting.llm import load_pipeline
from prompting.llm import HuggingFaceLLM

# import base miner class which takes care of most of the boilerplate
from neurons.miner import Miner


class ZephyrMiner(Miner):
    """
    Your miner neuron class. You should use this class to define your miner's behavior. In particular, you should replace the forward function with your own logic. You may also want to override the blacklist and priority functions according to your needs.

    This class inherits from the BaseMinerNeuron class, which in turn inherits from BaseNeuron. The BaseNeuron class takes care of routine tasks such as setting up wallet, subtensor, metagraph, logging directory, parsing config, etc. You can override any of the methods in BaseNeuron if you need to customize the behavior.

    This class provides reasonable default behavior for a miner such as blacklisting unrecognized hotkeys, prioritizing requests based on stake, and forwarding requests to the forward function. If you need to define custom
    """

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        """
        Adds OpenAI-specific arguments to the command line parser.
        """
        super().add_args(parser)
        parser.add_argument(
            "--neuron.model_id",
            type=str,
            default="HuggingFaceH4/zephyr-7b-beta",            
        )

        parser.add_argument(
            "--wandb.on",
            type=bool,
            default=False,
            help="Enable wandb logging.",
        )

        parser.add_argument(
            "--wandb.entity",
            type=str,
            default="sn1",
            help="Wandb entity to log to.",
        )

        parser.add_argument(
            "--wandb.project_name",
            type=str,
            default="miners_experiments",
            help="Wandb project to log to.",
        )

    def __init__(self, config=None):
        super().__init__(config=config)

        self.llm_pipeline = load_pipeline(
            model_id=self.config.neuron.model_id,
            torch_dtype=torch.bfloat16,
            device=self.device,
            mock=self.config.mock,
        )

        self.model = HuggingFaceLLM(
            llm_pipeline=self.llm_pipeline,
            system_prompt=self.config.neuron.system_prompt,
            max_new_tokens=self.config.neuron.max_tokens,
            do_sample=self.config.neuron.do_sample,
            temperature=self.config.neuron.temperature,
            top_k=self.config.neuron.top_k,
            top_p=self.config.neuron.top_p,
        )

    async def forward(
        self, synapse: PromptingSynapse
    ) -> PromptingSynapse:
        """
        Processes the incoming synapse by performing a predefined operation on the input data.
        This method should be replaced with actual logic relevant to the miner's purpose.

        Args:
            synapse (PromptingSynapse): The synapse object containing the 'dummy_input' data.

        Returns:
            PromptingSynapse: The synapse object with the 'dummy_output' field set to twice the 'dummy_input' value.

        The 'forward' function is a placeholder and should be overridden with logic that is appropriate for
        the miner's intended operation. This method demonstrates a basic transformation of input data.
        """
        
        try:
            t0 = time.time()
            bt.logging.debug(f"📧 Message received, forwarding synapse: {synapse}")

            prompt = synapse.messages[-1]
            bt.logging.debug(f"💬 Querying openai: {prompt}")
            response = self.model.query(
                message=prompt, # For now we just take the last message
                cleanup=True,
                role="user",
                disregard_system_prompt=False,

            )
            synapse.completion = response
            synapse_latency = time.time() - t0

            if self.config.wandb.on:
                self.log_event(
                    timing=synapse_latency, 
                    prompt=prompt,
                    completion=response,
                    system_prompt=self.system_prompt
                )
                        
            bt.logging.debug(f"✅ Served Response: {response}")
            torch.cuda.empty_cache()
        except Exception as e:
            bt.logging.error(f"Error: {e}")            
            synapse.completion = "Error: " + str(e)
        finally:
            return synapse
        
        


# This is the main function, which runs the miner.
if __name__ == "__main__":
    with ZephyrMiner() as miner:
        while True:
            bt.logging.info("Miner running...", time.time())
            time.sleep(5)
