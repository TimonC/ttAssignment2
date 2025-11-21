For RU course "Testing Techniques", we copied the python implementation of the generic adapter module from https://github.com/Axini/smartdoor-adapter-python.
We created an implementation of the AbstractHandler class to connect to the Axini modelling platform with our SUT, a local-hosted Synapse matrix home server.

Instead of setting up a websocket to connect directly to the Synapse server, we simply reuse the mock client from the first assignment,  https://github.com/TimonC/ttAssignment1.
The labels aren't forwarded directly to the SUT after conversion in *_label2message()*. Instead, we import the mock client as a module, and then within 
*_label2message()* we call those functions to send HTTP API requests to the SUT. This way, we can mock an Adapter with a websocket connection to a Matrix client,
allowing us to test the Matrix Client-Server API's as implemented in Synapse, using the Axini modelling platform.

We reuse the Bash shell script from the first assignment (src/ttAssignment1/setup_homeserver.h). Upon execution, the script kills any running container with the same name,
and also wipes the data volume to reset the user registrations. Inside our Handler, for every RESET we run the shell script, and then the handler polls the availability
of the home server, before signalling to Axini that it's ready for testing. We made no changes except we only make it setup one Synapse homeserver.


We have a bash script to help setup the virtual environment (./setup.sh), but these commands can also be run directly without a shell script.
These commands are the minimum Python libraries necessary for our mock adapter. For setting up the Synapse homeservers, a Linux environment with Docker and Bash is required.
We did not alter the mock client code itself for this asssignment. The only change to the setup script is that it only setups up one Synapse homeserver.

The adapter was launched as follows
```
chmod +x setup.sh
./setup.sh
source venv/bin/activate
export PYTHONPATH="$PYTHONPATH:~/ttAssignment2/src"                                                                                                                              
python3 src/adapter/plugin_adapter.py   -u $AXINI_ENDPOINT   -t $group10_API_KEY   -n group10
```
We did not include the actual axini endpoint or API key anywhere in this repository.
