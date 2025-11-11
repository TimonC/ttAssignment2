For RU course "Testing Techniques", we copied the python implementation of the generic adapter module from https://github.com/Axini/smartdoor-adapter-python.
We also copied their smartdoor adapter implementation as a base to build our own Matrix adapter, which can be found in src/adapter/matrix/
Specifically, we made an adapter for the mock Matrix client linked to our System Under Test, a local Synapse matrix home server.

This adapter connects to the Axini model-based testing platform via a websocket, allowing an AML model to generate and execute tests on our SUT.

We also simply copied the code =of our first assignment, for convenience and to import the mock client as a module easily. We did not alter the mock client for this assignment.
Check https://github.com/TimonC/ttAssignment1 for the setup of the local Synapse homeservers, a Linux environment with Bash, Docker and Python is required.

For the adapter, we have a bash script to help setup the virtual environment (./setup.sh), but these commands can also be run directly without a shell script.
Therefore, the only requirements for launching the adapter are Python, as well as that the Synapse homeservers are exposed on the same host.
Moreover, the Axini endpoint and API key are required to set it up. We did not include our group keys in this repository. 

The adapter was launched as follows
```
chmod +x setup.sh
./setup.sh
source venv/bin/activate
export PYTHONPATH="$PYTHONPATH:~/ttAssignment2/src"                                                                                                                              
python3 src/adapter/plugin_adapter.py   -u $AXINI_ENDPOINT   -t $group10_API_KEY   -n MockClientAdapter
```
