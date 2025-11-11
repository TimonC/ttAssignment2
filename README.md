For RU course "Testing Techniques", we copied the python implementation of the generic adapter module from https://github.com/Axini/smartdoor-adapter-python.

We also simply copied the code for the first assignment, for convenience to import it as a module. 
Check  https://github.com/TimonC/ttAssignment1 for the setup, a Linux environment with Bash, Docker and Python is required.

For the adapter, we have a bash script to help setup the virtual environment (./setup.sh), but these commands can also be run directly without a shell script.
Therefore, the only requirements for launching the adapter are Python, as well as that the Synapse homeservers are exposed on the same host.
Moreover, the Axini endpoint and API key are required to set it up. We did not include our group keys in this repository. 

The adapter was launched as follows
```
chmod +x setup.sh
./setup.sh
source venv/bin/activate
export PYTHONPATH="$PYTHONPATH:~/ttAssignment2/src"                                                                                                                              
python3 src/adapter/plugin_adapter.py   -u $AXINI_ARI   -t "$group10_API_KEY"   -n MockClientAdapter
```
