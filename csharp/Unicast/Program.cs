// Copyright (C) 2026, IDS Imaging Development Systems GmbH.
//
// Permission to use, copy, modify, and/or distribute this software for
// any purpose with or without fee is hereby granted.
//
// THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
// WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
// OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
// FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
// DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
// AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
// OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

using System;
using System.Collections.Generic;
using IDSImaging.Peak.API;
using IDSImaging.Peak.API.Core;
using IDSImaging.Peak.API.Core.Nodes;
using IDSImaging.Peak.API.Std;

namespace IDSImaging.Peak.Examples.Unicast
{
    /// <summary>
    /// This example demonstrates how to use the unicast discovery
    /// features of the transport layer (TL) to locate cameras that
    /// are not in the same subnet as the host system.
    ///
    /// Unlike standard discovery mechanisms that rely on broadcast
    /// traffic, this example shows how to explicitly target devices
    /// via their IP addresses.
    /// </summary>
    internal static class Program
    {
        private static readonly List<ProducerLibrary> _gProducers = new List<ProducerLibrary>();
        private static readonly List<IDSImaging.Peak.API.Core.System> _gSystems = new List<IDSImaging.Peak.API.Core.System>();
        private static readonly List<Interface> _gInterfaces = new List<Interface>();

        private static int Main()
        {
            // The library must be initialized before use.
            // Each `Initialize` call must be matched with a corresponding call
            // to `Close`.
            Library.Initialize();

            try
            {
                var interfaces = GetInterfaces();
                if (interfaces.Count == 0)
                {
                    Console.WriteLine("No interfaces found.");
                    WaitForEnter();
                    Library.Close();
                    return 0;
                }

                var selectedInterface = SelectInterface(interfaces);
                Console.WriteLine($"Selected Interface: {selectedInterface.DisplayName()}");

                var unicastIpAddresses = GetIpAddresses();

                // NOTE: Devices will only be discovered via unicast, so that no broadcasts are sent.
                //       Therefore, only devices with IP addresses entered above will be found.
                //       Also, this will only list GigEVision devices, USB devices will not be searched for.
                var deviceDescriptors = FindDevicesViaUnicast(selectedInterface, unicastIpAddresses);

                if (deviceDescriptors.Count == 0)
                {
                    Console.WriteLine("Did not find any devices.");
                }
                else
                {
                    Console.WriteLine("Found Devices:");
                    PrintDevices(deviceDescriptors);
                }

                WaitForEnter();
            }
            catch (Exception e)
            {
                Console.WriteLine($"EXCEPTION: {e}");
            }
            finally
            {
                // Each `Initialize` call must be matched with a corresponding call
                // to `Close`.
                Library.Close();
            }

            return 0;
        }
        /// <summary>
        /// Print device information of given devices.
        /// </summary>
        /// <param name="devices">Devices to be listed.</param>
        private static void PrintDevices(List<DeviceDescriptor> devices)
        {
            foreach (var device in devices)
            {
                var openable = device.IsOpenable() ? "Openable" : "No Access";
                Console.WriteLine($"{device.DisplayName()}({openable}) | {device.ParentInterface().DisplayName()} -> \"{device.ParentInterface().ParentSystem().CTIFullPath()}\"");
            }
        }

        /// <summary>
        /// Get the IP addresses of the devices we will be looking for.
        ///
        /// This prompts the user to enter IP addresses for discovery.
        /// </summary>
        /// <returns>List of IP addresses.</returns>
        private static List<uint> GetIpAddresses()
        {
            var unicastIpAddresses = new List<uint>();

            Console.WriteLine("Please enter the IP addresses of the devices you want to find. Press Enter without input to continue.");

            while (true)
            {
                Console.Write("Enter IP Address: ");
                var ipAddress = Console.ReadLine();

                if (string.IsNullOrWhiteSpace(ipAddress))
                    break;

                if (!IsIpAddressValid(ipAddress))
                {
                    Console.WriteLine("Invalid input.");
                    continue;
                }

                unicastIpAddresses.Add(IpStrToInt(ipAddress));
            }

            return unicastIpAddresses;
        }

        /// <summary>
        /// Prompt the user to select an interface from a list.
        /// </summary>
        /// <param name="interfaces">List of interfaces to be selected from.</param>
        /// <returns>The selected interface.</returns>
        private static Interface SelectInterface(List<Interface> interfaces)
        {
            while (true)
            {
                for (var i = 0; i < interfaces.Count; i++)
                {
                    var iface = interfaces[i];
                    Console.WriteLine($"{i} | {iface.DisplayName()} -> \"{iface.ParentSystem().CTIFullPath()}\"");
                }

                Console.Write("\nSelect Interface: ");
                if (int.TryParse(Console.ReadLine(), out var selectedIndex) && selectedIndex >= 0 && selectedIndex < interfaces.Count)
                {
                    return interfaces[selectedIndex];
                }

                Console.WriteLine("Invalid input.");
            }
        }

        /// <summary>
        /// Check if the provided string is a valid IP address.
        /// </summary>
        /// <param name="ipString">String to check.</param>
        /// <returns>True if valid.</returns>
        private static bool IsIpAddressValid(string ipString)
        {
            if (string.IsNullOrEmpty(ipString))
            {
                return false;
            }

            var parts = ipString.Split('.');
            if (parts.Length != 4)
            {
                return false;
            }

            foreach (var part in parts)
            {
                if (!int.TryParse(part, out var byteVal) || byteVal < 0 || byteVal > 255)
                {
                    return false;
                }
            }

            return true;
        }

        /// <summary>
        /// Convert an IP address from its string representation into an integer.
        /// </summary>
        /// <param name="ipString">The IP address as a string.</param>
        /// <returns>The IP address as an integer.</returns>
        private static uint IpStrToInt(string ipString)
        {
            if (!IsIpAddressValid(ipString))
            {
                throw new ArgumentException($"Invalid IP address: {ipString}");
            }

            var parts = ipString.Split('.');
            uint ipInt = 0;

            foreach (var part in parts)
            {
                ipInt = (ipInt << 8) | uint.Parse(part);
            }

            return ipInt;
        }

        /// <summary>
        /// Configure the discovery settings of the given interface.
        ///
        /// Configures the given interface by adding explicit device IP addresses to be discovered using unicast,
        /// and optionally enabling broadcast-based discovery.
        /// </summary>
        /// <param name="iface">Interface to configure.</param>
        /// <param name="allowBroadcast">
        /// Allow sending a discovery via broadcast and allow a device to answer via broadcast, if it decides to.
        /// </param>
        /// <param name="ipAddresses">IP addresses to send a unicast discovery to on this interface.</param>
        private static void ConfigureInterface(Interface iface, bool allowBroadcast, List<uint> ipAddresses)
        {
            var interfaceNodeMap = iface.NodeMaps()[0];

            var nodeUnicastAddressToAdd = interfaceNodeMap.TryFindNode<IntegerNode>("GevDiscoveryUnicastIPAddressToAdd");
            var nodeUnicastAddressAdd = interfaceNodeMap.TryFindNode<CommandNode>("GevDiscoveryUnicastIPAddressAdd");
            var nodeAllowDiscoveryAckBroadcast = interfaceNodeMap.TryFindNode<BooleanNode>("GevAllowDiscoveryACKBroadcast");
            var nodeAllowDiscoveryCmdBroadcast = interfaceNodeMap.TryFindNode<BooleanNode>("GevAllowDiscoveryCMDBroadcast");

            // Configure Unicast addresses, if supported by the transport layer (TL)
            if (nodeUnicastAddressToAdd != null && nodeUnicastAddressAdd != null)
            {
                foreach (var ip in ipAddresses)
                {
                    nodeUnicastAddressToAdd.SetValue(ip);
                    nodeUnicastAddressAdd.Execute();
                }
            }
            else
            {
                Console.WriteLine($"WARNING: Interface \"{iface.DisplayName()} -> {iface.ParentSystem().CTIFullPath()}\" does not support unicast discovery.");
            }

            // Configure whether broadcast is allowed, if supported by the TL
            if (nodeAllowDiscoveryCmdBroadcast != null && nodeAllowDiscoveryAckBroadcast != null)
            {
                nodeAllowDiscoveryCmdBroadcast.SetValue(allowBroadcast);
                nodeAllowDiscoveryAckBroadcast.SetValue(allowBroadcast);
            }
            else
            {
                Console.WriteLine($"WARNING: Interface \"{iface.DisplayName()} -> {iface.ParentSystem().CTIFullPath()}\" does not support disabling the broadcast.");
            }
        }

        /// <summary>
        /// Filter out all interfaces other than GigEVision.
        /// </summary>
        /// <param name="interfaceDescriptors">Descriptors of the interfaces to be filtered.</param>
        /// <returns>Interfaces that are of type GigEVision.</returns>
        private static List<Interface> FilterInterfaces(InterfaceDescriptorCollection interfaceDescriptors)
        {
            var filteredInterfaces = new List<Interface>();

            foreach (var descriptor in interfaceDescriptors)
            {
                var iface = descriptor.OpenInterface();
                var interfaceNodeMap = iface.NodeMaps()[0];

                var interfaceTypeNode = interfaceNodeMap.FindNode<EnumerationNode>("InterfaceType");
                var interfaceType = interfaceTypeNode.CurrentEntry().StringValue();

                // Filter out all interfaces that are not GigEVision
                if (interfaceType != "GigEVision")
                {
                    continue;
                }

                filteredInterfaces.Add(iface);
            }

            return filteredInterfaces;
        }

        /// <summary>
        /// Gather all interfaces of all transport layers found on the system.
        ///
        /// For the purpose of this example, only GigEVision interfaces will be included.
        /// </summary>
        /// <returns>List of all GigEVision interfaces.</returns>
        private static List<Interface> GetInterfaces()
        {
            // Get Paths of the installed transport layers
            var ctiPaths = EnvironmentInspector.CollectCTIPaths();

            foreach (var ctiPath in ctiPaths)
            {
                try
                {
                    var producer = ProducerLibrary.Open(ctiPath);
                    var systemDescriptor = producer.System();
                    var system = systemDescriptor.OpenSystem();

                    system.UpdateInterfaces(500);

                    var interfaceDescriptors = system.Interfaces();
                    var filteredInterfaces = FilterInterfaces(interfaceDescriptors);

                    if (filteredInterfaces.Count > 0)
                    {
                        _gProducers.Add(producer);
                        _gSystems.Add(system);
                        _gInterfaces.AddRange(filteredInterfaces);
                    }
                }
                catch (Exception e)
                {
                    Console.WriteLine($"Failed to load and open cti: {ctiPath} with error: {e.Message}");
                }
            }

            return _gInterfaces;
        }

        /// <summary>
        /// Search for devices via unicast and without broadcast.
        ///
        /// Only GigEVision (GEV) devices will be searched. A device will only be found if it replies to the unicast discovery.
        /// </summary>
        /// <param name="iface">Interface on which the unicast is to be sent.</param>
        /// <param name="unicastDeviceIpAddresses">IP addresses of the devices to be discovered.</param>
        /// <returns>List of device descriptors of the devices that have been found.</returns>
        private static List<DeviceDescriptor> FindDevicesViaUnicast(Interface iface, List<uint> unicastDeviceIpAddresses)
        {
            var foundDevices = new List<DeviceDescriptor>();

            // Configure interfaces to discover via unicast and unicast only
            ConfigureInterface(iface, false, unicastDeviceIpAddresses);

            // Send device discoveries and listen for replies
            iface.UpdateDevices(1000);

            var deviceDescriptors = iface.Devices();

            foundDevices.AddRange(deviceDescriptors);

            return foundDevices;
        }

        /// <summary>
        /// Wait for the user to press the Enter key.
        ///
        /// This function is called from Main whenever the program exits—either due to an error or normal termination.
        /// </summary>
        private static void WaitForEnter()
        {
            Console.WriteLine();
            Console.WriteLine("Press Enter to continue...");
            Console.ReadLine();
        }
    }
}
