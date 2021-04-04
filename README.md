# junos_showCountersCascade
This script was intended to be used in a classic 3-tier Juniper DC (with L3 resident on core layer) but it should work also in other environment as long as the core ip inserted is where the L3 resides.

Given a target IP, makes a .txt report with all the interface errors in the path Core>target IP.  
It doesn't show the errors of the interfaces pointing "upwards" since the script was built to dig towards the target IP, but it would be fairly easy to implement this feature since there are all the tools to do it.

-Input: IP of the device (one end of the problematic communication, the other is often outside of the DC) + user/pass authentication + mgmt IP of one of the core.

-execution: connects to the peer switch (if any), and via ARP/MAC table search the errors on the respective interfaces (physical+aggregates), then it find (via LLDP and its parameters) and connects to the switches of the inferior level, and the process is repeated util it find the final device at the access layer.

-output: a .txt file with all the interface statistics/error of the interfaces present in the path towards the host.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install requirements.txt.

```bash
python -m pip install -r requirements.txt
```

## Usage

```python
py showCountersCascade.py
```

Then you will find the results in the same folder of the script.

## Contributing
Please open an issue first to discuss what you would like to change. 

## License
[GPL-3.0](https://choosealicense.com/licenses/gpl-3.0/)
