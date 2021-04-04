from pprint import pprint
from jnpr.junos import *
from datetime import datetime
from getpass import getpass
import sys


# functions start #


def get_phyIntFromArp(device, target):
    '''
    :param device: jnpr.junos Device object
    :param target: ip address (string) target of the search
    :return: physical interface (string) of the device where the ip address is seen through ARP and MAC table
    '''
    global mac_target  # remove global var?
    showArp = device.rpc.get_arp_table_information(no_resolve=True)
    for i in showArp.xpath('arp-table-entry'):  # visit the list with the arp table
        if (i.findtext('ip-address')) == target:  # if target ip is found in arp, save the mac associated
            pprint("get_phyIntFromArp: device " + target + " has MAC " + i.findtext('mac-address'))
            mac_target = i.findtext('mac-address')
    if mac_target is None:  # if no mac is found set exit_code=1 and exit from function
        raise ValueError("get_phyIntFromArp: MAC not present")
    showmac = device.rpc.get_ethernet_switching_table_information()
    for p in showmac.iter('l2ng-mac-entry'):  # with the mac retrieved before, find the physical int associated
        if (p.findtext('l2ng-l2-mac-address')) == mac_target:
            interface = (p.findtext('l2ng-l2-mac-logical-interface')).split('.')
            phy_interface = interface[0]
            return phy_interface
    return "get_intFromArp: MAC presente in ARP ma non in ethernet-switching table"


def get_phyIntFromMac(device):
    '''
    :param device: jnpr.junos Device object
    :return: physical interface (string) from where the MAC is seen (the MAC searched is the one in global variable
             mac_target)
    '''
    showmac = device.rpc.get_ethernet_switching_table_information()
    for p in showmac.iter('l2ng-mac-entry'):  # slides the ethernet-switching table
        if (p.findtext('l2ng-l2-mac-address')) == mac_target: # if MAC is found
            interface = (p.findtext('l2ng-l2-mac-logical-interface')).split('.')
            phy_interface = interface[0]
            return phy_interface
    return "get_intFromMac: MAC is present"


def isMacPresentFromArp(device, target):
    '''
    :param device: jnpr.junos Device object
    :param target: target IP (string)
    :return: True if target device is found under MAC table (via ARP table>MAC table), False if it's not found under MAC
             table
    '''
    mac_target = None
    showArp = device.rpc.get_arp_table_information(no_resolve=True)
    for i in showArp.xpath('arp-table-entry'):  # slides the arp table
        # if it finds the target IP in the arp table, saves MAC and search for it in MAC table
        if (i.findtext('ip-address')) == target:
            mac = i.findtext('mac-address')
            if isMacPresent(device,mac) is True:
                return True
    if mac_target is None:
        return False


def isMacPresent(device, mac):
    '''
    :param device: jnpr.junos Device object
    :param mac: target MAC (string)
    :return: True if MAC is present under MAC table, False if not
    '''
    showmac = device.rpc.get_ethernet_switching_table_information()
    for p in showmac.iter('l2ng-mac-entry'):
        if (p.findtext('l2ng-l2-mac-address')) == mac:
            return True
    return False


def get_lacpMembers(device, interface):
    '''
    :param device: jnpr.junos Device object
    :param interface: aggregate name (string)
    :return: list of LACP memebers
    '''
    list = []
    showlacp = device.rpc.get_lacp_interface_information()
    for i in showlacp.iter('lacp-interface-information'):
        if (i.findtext('lag-lacp-header/aggregate-name')) == interface:
            for p in i.iter('lag-lacp-protocol'):
                list.append(p.findtext('name'))
            return list


def get_iccpPeerIP(device):
    '''
    :param device: jnpr.junos Device object
    :return: IP of the device ICCP peer
    '''
    showiccp = device.rpc.get_config()
    for i in showiccp.iter('iccp'):
        # select backup peer IP because it's the OoB, the main one is local to the devices
        x = i.findtext('peer/backup-liveness-detection/backup-peer-ip')
        return x


def isIccpPeerPresent(device):
    '''
    :param device: jnpr.junos Device object
    :return: True if backup ICCP peer is present, False if it's not
    '''
    x = None
    showiccp = device.rpc.get_config()
    for i in showiccp.iter('iccp'):
        x = i.findtext('peer/backup-liveness-detection/backup-peer-ip')
    if x is None:
        return False
    else:
        return True


def get_lldpMgmtIP(device, interface):
    '''
    :param device: jnpr.junos Device object
    :param interface: the interface (string) to look on for LLDP
    :return: remote management IP (string) of the device seen via LLDP on the interface selected
    '''
    showlldp = device.rpc.get_lldp_interface_neighbors(interface_device=interface)
    mgmt_ip = showlldp.findtext('lldp-neighbor-information/lldp-remote-management-address')
    return mgmt_ip


def save_intErrors(device, interface, file):
    '''
    :param device: jnpr.junos Device object
    :param interface: interface (string) where we need to extract errors, could be both physical and LACP
    :param file: file object that has been opened, to write on the interface's errors
    :return: it doesn't return a value but writes on the file all the wanted info
    '''
    intInfo = device.rpc.get_interface_information(interface_name=interface, extensive=True)

    file.write("\n" + interface + "\nInput error list:\n")
    input_errors = intInfo.findtext('physical-interface/input-error-list/input-errors')
    input_drops = intInfo.findtext('physical-interface/input-error-list/input-drops')
    framing_errors = intInfo.findtext('physical-interface/input-error-list/framing-errors')
    input_runts = intInfo.findtext('physical-interface/input-error-list/input-runts')
    file.write("\tinput-errors: " + input_errors + "\n\tinput-drops: " + input_drops + "\n\tframing-errors: " +
               framing_errors + "\n\tinput runts: " + input_runts + "\n")
    if interface.startswith("ae") == True:  # if aggregate
        input_giants = intInfo.findtext('physical-interface/input-error-list/input-giants')
        input_discards = intInfo.findtext('physical-interface/input-error-list/input-discards')
        file.write("\tinput-giants: " + input_giants + "\n\tinput-discards: " + input_discards + "\n")
    else:  # else, it's physical interface
        input_discards = intInfo.findtext('physical-interface/input-error-list/input-discards')
        input_l3_incompletes = intInfo.findtext('physical-interface/input-error-list/input-l3-incompletes')
        input_l2_channel_errors = intInfo.findtext('physical-interface/input-error-list/input-l2-channel-errors')
        input_l2_mismatch_timeouts = intInfo.findtext('physical-interface/input-error-list/input-l2-mismatch-timeouts')
        input_fifo_errors = intInfo.findtext('physical-interface/input-error-list/input-fifo-errors')
        file.write("\tinput-discards: " + input_discards + "\n\tinput-l3-incompletes: " + input_l3_incompletes +
                   "\n\tinput-l2-channel-errors: " + input_l2_channel_errors + "\n\tinput-l2-mismatch-timeouts: " +
                   input_l2_mismatch_timeouts + "\n\tinput-fifo-errors: " + input_fifo_errors + "\n")
    input_resource_errors = intInfo.findtext('physical-interface/input-error-list/input-resource-errors')
    file.write("\tinput-resource-errors: " + input_resource_errors + "\n")

    file.write("Output error list:\n")
    carrier_transitions = intInfo.findtext('physical-interface/output-error-list/carrier-transitions')
    output_errors = intInfo.findtext('physical-interface/output-error-list/output-errors')
    file.write("\tcarrier-transitions: " + carrier_transitions + "\n\toutput-errors: " + output_errors + "\n")
    if interface.startswith("ae") == True:  # if aggregate
        output_drops = intInfo.findtext('physical-interface/output-error-list/output-drops')
        mtu_errors = intInfo.findtext('physical-interface/output-error-list/mtu-errors')
        file.write("\toutput-drops: " + output_drops + "\n\tmtu-errors: " + mtu_errors + "\n")
    else:  # else, it's physical interface
        output_collisions = intInfo.findtext('physical-interface/output-error-list/output-collisions')
        output_drops = intInfo.findtext('physical-interface/output-error-list/output-drops')
        aged_packets = intInfo.findtext('physical-interface/output-error-list/aged-packets')
        mtu_errors = intInfo.findtext('physical-interface/output-error-list/mtu-errors')
        hs_link_crc_errors = intInfo.findtext('physical-interface/output-error-list/hs-link-crc-errors')
        output_fifo_errors = intInfo.findtext('physical-interface/output-error-list/output-fifo-errors')
        file.write(
            "\toutput-collisions: " + output_collisions + "\n\toutput-drops: " + output_drops + "\n\taged-packets: " +
            aged_packets + "\n\tmtu-errors: " + mtu_errors + "\n\ths-link-crc-errors: " + hs_link_crc_errors +
            "\n\toutput-fifo-errors: " + output_fifo_errors + "\n")
    output_resource_errors = intInfo.findtext('physical-interface/output-error-list/output-resource-errors')
    file.write("\toutput-resource-errors: " + output_resource_errors + "\n")

    file.write("Queue counters errors:\n")
    for i in intInfo.iter('queue'):
        forwarding_class_name = i.findtext('forwarding-class-name')
        queue_counters_total_drop_packets = i.findtext('queue-counters-total-drop-packets')
        file.write("\t" + forwarding_class_name + " drops: " + queue_counters_total_drop_packets + "\n")
    if interface.startswith("ae") == False:
        bit_error_seconds = intInfo.findtext('physical-interface/ethernet-pcs-statistics/bit-error-seconds')
        errored_blocks_seconds = intInfo.findtext('physical-interface/ethernet-pcs-statistics/errored-blocks-seconds')
        file.write("ethernet-pcs-statistics:\n\tbit-error-seconds: " + bit_error_seconds +
                   "\n\terrored-blocks-seconds: " + errored_blocks_seconds + "\n")

        fec_ccw_error_rate = intInfo.findtext('physical-interface/ethernet-fec-statistics/fec_ccw_error_rate')
        fec_nccw_error_rate = intInfo.findtext('physical-interface/ethernet-fec-statistics/fec_nccw_error_rate')
        file.write("ethernet-fec-statistics:\n\tfec_ccw_error_rate: " + fec_ccw_error_rate +
                   "\n\tfec_nccw_error_rate: " + fec_nccw_error_rate + "\n")

        input_crc_errors = intInfo.findtext('physical-interface/ethernet-mac-statistics/input-crc-errors')
        output_crc_errors = intInfo.findtext('physical-interface/ethernet-mac-statistics/output-crc-errors')
        input_fifo_errors = intInfo.findtext('physical-interface/ethernet-mac-statistics/input-fifo-errors')
        output_fifo_errors = intInfo.findtext('physical-interface/ethernet-mac-statistics/output-fifo-errors')
        file.write("ethernet-mac-statistics:\n\tinput-crc-errors: " + input_crc_errors + "\n\toutput-crc-errors: " +
                   output_crc_errors +"\n\tinput-fifo-errors: " + input_fifo_errors + "\n\toutput-fifo-errors: " +
                   output_fifo_errors + "\n")
    file.flush()


# functions end


exit_code = False  # used as escape variable to block the device scan
mac_target = None  # it will contain the MAC to be searched
#ip_device1 = "" #commented out since acquired via input below
ip_device2 = None

timenow = str(datetime.now().strftime("%d-%m-%Y %H-%M-%S"))
txtfile = open("Report " + timenow + ".txt", "w")  # open file named with the hour
ip_device1=input("Insert your core management IP: ")
user = input("Username: ")
password = getpass("Password: ")
target_ip = input("Insert target IP: ")
txtfile.write(str(datetime.now().time()) + " REPORT IP " + target_ip + " starting from " + ip_device1 + "\n")

# ___________________________first dig where L3 resides________________________________#
device1 = Device(host=ip_device1, user=user, password=password, port=22)
try:  # open connection to the first device
    device1.open(normalize=True)
    pprint("Connected to device " + device1.facts['hostname'] + "(" + ip_device1 + ")")
    txtfile.write("\n" + str(datetime.now().time()) + " Connected to device " + device1.facts['hostname'] + "(" +
                  ip_device1 + ")\n")
except:
    sys.exit("Script aborted, There was a problem connecting to device " + ip_device1)

try:
    # check if MAC of the target is present under one of the two core
    if isMacPresentFromArp(device1, target_ip) == True or \
            (isIccpPeerPresent(device1) == True and isMacPresentFromArp(get_iccpPeerIP(device1), target_ip) == True) \
            == True:

        #save intErrors from device1 (of the interface that sees the target IP)
        try:
            physical1 = get_phyIntFromArp(device1, target_ip)
        except ValueError as error:
            pprint(device1.facts['hostname'] + error)
            txtfile.write(str(datetime.now().time()) +
                          " It's not possible to find the corresponding MAC via arp on the device " +
                          device1.facts['hostname'] + "(" + ip_device1 + ")\n")
        save_intErrors(device1, physical1, txtfile)

        #if aggregate, save intErrors from device1 of the interfaces part of the LACP (that points the target IP) and
        #saves mgmt IP of the child device, else only saves mgmt IP of the child device
        if physical1.startswith("ae") == True:
            list_int = get_lacpMembers(device1, physical1)
            for i in range(len(list_int)):  # saves intErrors of each physical interfaces part of the aggregate
                save_intErrors(device1, list_int[i], txtfile)
            mgmt_child1 = get_lldpMgmtIP(device1, list_int[0])  # saves mgmt IP of the child from aggregate
        else:
            mgmt_child1 = get_lldpMgmtIP(device1, physical1)  # saves mgmt IP of the child from physical interface
        if mgmt_child1 != None:  # if there is mgmt child
            child1_present = True

        if isIccpPeerPresent(device1) == True: #if ICCP peer is present, it follows the same procedure as above
            ip_device2 = get_iccpPeerIP(device1)
            device2 = Device(host=ip_device2, user=user, password=password, port=22)
            try:
                device2.open(normalize=True)
                pprint("Connected to device " + device2.facts['hostname'] + "(" + get_iccpPeerIP(device1) + ")")
                txtfile.write("\n" + str(datetime.now().time()) + " Connected to device " + "(" +
                              device2.facts['hostname'] + ")\n")
            except ConnectionError as error:
                pprint("There was a problem connecting to device " + ip_device2)
                txtfile.write("\n" + str(datetime.now().time()) + " There was a problem connecting to device " +
                              ip_device2 + "\n\n")
            # save intErrors from device1 peer (of the interface that sees the target IP)
            try:
                physical2 = get_phyIntFromArp(device2, target_ip)
            except ValueError as error:
                pprint(device2.facts['hostname'] + error)
                txtfile.write(str(datetime.now().time()) +
                              " It's not possible to find the corresponding MAC via arp on the device " +
                              device2.facts['hostname'] + "(" + ip_device2 + ")\n")
            save_intErrors(device2, physical2, txtfile)

            # if aggregate, save intErrors from device1 peer, of the interfaces part of the LACP (that points the
            # target IP) and saves mgmt IP of the child device, else only saves mgmt IP of the child device
            if physical2.startswith("ae") == True:
                list_int = get_lacpMembers(device2, physical2)
                for i in range(len(list_int)):
                    save_intErrors(device2, list_int[i], txtfile)
                mgmt_child2 = get_lldpMgmtIP(device2, list_int[0])
            if mgmt_child2 != None: # if there is mgmt child
                child2_present = True

        # if child towards the target IP are present, save their mgmt to connect later,
        # else only close the currect connection and end the script
        if (child1_present == True or child2_present == True):
            # if one of the child is present, save its IP into ip_device1 (which will be the next starting point to
            # dig further)
            if child1_present == True:
                ip_device1 = mgmt_child1
            if child2_present == True:
                ip_device1 = mgmt_child2
        else:
            exit_code = True

        #close connection with the devices
        try:
            device1.close()
        except ConnectionError as error:
            pprint(error)
        try:
            device2.close()
        except ConnectionError as error:
            pprint(error)

        txtfile.flush()

    else:  # target MAC not found on both core
        device1.close()
        pprint("target MAC/device not present under these devices")
        exit_code = True

except:
    sys.exit("Undefined Error")
# ___________________________end of first dig (where L3 resides)________________________________#

# Since the core of this section is the same as the one above (the difference is that in the one above starts from ARP
# and the one below from MAC) I've avoided to repeat the comments, the operations are the same (I should consider
# to re-organize the code to avoid this big repetition)

while exit_code is False:  #since it remains False, the dig continue
    child1_present = False
    child2_present = False
    device1 = Device(host=ip_device1, user=user, password=password, port=22)
    try:
        device1.open(normalize=True)
        pprint("Connected to device " + device1.facts['hostname'] + "(" + ip_device1 + ")")
        txtfile.write("\n" + str(datetime.now().time()) + " Connected to device " + device1.facts['hostname'] +
                      "(" + ip_device1 + ")\n")
    except ConnectionError:
        pprint("There was a problem connecting to device " + ip_device1)
        txtfile.write("\n" + str(datetime.now().time()) + " There was a problem connecting to device " +
                      ip_device1 + "\n\n")
        exit_code = True
        break

    # check if MAC is present under one of the two device
    if isMacPresent(device1, mac_target) == True or \
            (isIccpPeerPresent(device1) == True and isMacPresent(get_iccpPeerIP(device1), mac_target) == True) == True:

        try:
            physical1 = get_phyIntFromMac(device1)
        except ValueError as error:
            pprint(device1.facts['hostname'] + error)
            txtfile.write(str(datetime.now().time()) +
                          " It's not possible to find the corresponding MAC via arp on the device " +
                          device1.facts['hostname'] + "(" + ip_device1 + ")\n")
        save_intErrors(device1, physical1, txtfile)

        if physical1.startswith("ae") == True:
            list_int = get_lacpMembers(device1, physical1)
            for i in range(len(list_int)):
                save_intErrors(device1, list_int[i], txtfile)
            mgmt_child1 = get_lldpMgmtIP(device1, list_int[0])
        else:
            mgmt_child1 = get_lldpMgmtIP(device1, physical1)
        if mgmt_child1 != None:
            child1_present = True

        if isIccpPeerPresent(device1) == True:
            ip_device2 = get_iccpPeerIP(device1)
            device2 = Device(host=ip_device2, user=user, password=password, port=22)
            try:
                device2.open(normalize=True)
                pprint("Connected to device " + device2.facts['hostname'] + "(" + get_iccpPeerIP(device1) + ")")
                txtfile.write("\n" + str(datetime.now().time()) + " Connected to device " + "(" + device2.facts['hostname'] + ")\n")
            except ConnectionError as error:
                pprint("There was a problem connecting to device " + ip_device2)
                txtfile.write("\n" + str(datetime.now().time()) + " There was a problem connecting to device " + ip_device2 + "\n\n")
            try:
                physical2 = get_phyIntFromMac(device2)
            except ValueError as error:
                pprint(device2.facts['hostname'] + error)
                txtfile.write(str(datetime.now().time()) +
                              " It's not possible to find the corresponding MAC via arp on the device " +
                              device2.facts['hostname'] + "(" + ip_device2 + ")\n")
            save_intErrors(device2, physical2, txtfile)
            if physical2.startswith("ae") == True:
                list_int = get_lacpMembers(device2, physical2)
                for i in range(len(list_int)):
                    save_intErrors(device2, list_int[i], txtfile)
                mgmt_child2 = get_lldpMgmtIP(device2, list_int[0])
            if mgmt_child2 != None:
                child2_present = True
            else:
                mgmt_child2 = get_lldpMgmtIP(device2, physical2)

        if (child1_present == True or child2_present == True):
            if child1_present == True:
                ip_device1 = mgmt_child1
            if child2_present == True:
                ip_device1 = mgmt_child2
            if child1_present != True or child2_present != True:
                exit_code = True
        else:
            exit_code = True

        try:
            device1.close()
        except ConnectionError as error:
            pprint(error)
        try:
            device2.close()
        except ConnectionError as error:
            pprint(error)

        txtfile.flush()
    else:  # target MAC not found on both devices
        device1.close()
        pprint("target MAC/device not present under these devices")
        exit_code = True
txtfile.close()
