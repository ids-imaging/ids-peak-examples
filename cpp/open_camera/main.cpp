/*
 * Copyright(C) 2026, IDS Imaging Development Systems GmbH.
 *
 * Permission to use, copy, modify, and/or distribute this software for
 * any purpose with or without fee is hereby granted.
 *
 * THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
 * WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
 * FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
 * DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
 * AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
 * OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

/*!
 * \brief This application demonstrates how to use the device manager to open a camera
 */

#include <peak/peak.hpp>

#include <cstddef>
#include <cstdlib>
#include <iostream>

namespace
{
void WaitForEnterPressed();
std::string TryReadString(peak::core::NodeMap& nodeMap, const std::string& nodeName);
} // namespace

int main()
{
    std::cout << "IDS peak OpenCamera example\n";

    try
    {
        // The library must be initialized before use.
        // Each call to `Initialize` must be matched with a corresponding call to `Close`.
        peak::Library::Initialize();

        // Get the device manager singleton object.
        auto& deviceManager = peak::DeviceManager::Instance();

        // Update the device manager.
        // When `Update` is called, it searches for all ProducerLibraries contained
        // in the directories specified by the GENICAM_GENTL{32/64}_PATH environment variable.
        // It then opens all found producers, their systems, interfaces, and lists
        // all available DeviceDescriptors.
        deviceManager.Update();

        // Exit program if no device was found.
        if (deviceManager.Devices().empty())
        {
            std::cout << "No device found. Exiting program.\n";
            WaitForEnterPressed();
            // One call to `Close` is required for each call to `Initialize`.
            peak::Library::Close();
            return EXIT_SUCCESS;
        }

        // List all available devices.
        std::size_t i = 0;
        std::cout << "Devices available:\n";
        for (const auto& deviceDescriptor : deviceManager.Devices())
        {
            std::cout << i << ": " << deviceDescriptor->ModelName() << " ("
                      << deviceDescriptor->ParentInterface()->DisplayName() << "; "
                      << deviceDescriptor->ParentInterface()->ParentSystem()->DisplayName() << " v."
                      << deviceDescriptor->ParentInterface()->ParentSystem()->Version() << ")\n";
            ++i;
        }

        // Select a device to open.
        std::size_t selectedDevice = 0;

        // Prompt user for device index or remove this block to always use the first device.
        std::cout << "\nSelect device index to open [0-" << deviceManager.Devices().size() - 1 << "]: ";
        std::cin >> selectedDevice;

        if (std::cin.fail())
        {
            std::cout << "Invalid input! Using index 0." << std::endl;
            std::cin.clear();
            std::cin.ignore(1'000, '\n');
            selectedDevice = 0;
        }

        if (selectedDevice >= deviceManager.Devices().size())
        {
            std::cout << "Invalid index! Using index 0." << std::endl;
            selectedDevice = 0;
        }

        // Open the selected device with control access.
        // The access types correspond to the GenTL `DEVICE_ACCESS_FLAGS`.
        auto device = deviceManager.Devices().at(selectedDevice)->OpenDevice(peak::core::DeviceAccessType::Control);

        // Retrieve the remote device's primary node map.
        // In GenICam, a node map represents a hierarchical set of parameters (features)
        // such as exposure, gain, or firmware info. This node map provides access to controls
        // implemented on the device itself, typically following the GenICam SFNC, while still
        // allowing for vendor-specific extensions.
        auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);

        std::cout << "Model Name: " << TryReadString(*nodeMapRemoteDevice, "DeviceModelName") << "\n";
        std::cout << "User ID: " << TryReadString(*nodeMapRemoteDevice, "DeviceUserID") << "\n";
        std::cout << "Sensor Name: " << TryReadString(*nodeMapRemoteDevice, "SensorName") << "\n";

        try
        {
            // Print maximum sensor resolution (width x height).
            std::cout << "Max. resolution (w x h): "
                      << nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("WidthMax")->Value() << " x "
                      << nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("HeightMax")->Value() << "\n";
        }
        catch (const std::exception&)
        {
            std::cout << "Max. resolution (w x h): (unknown)\n";
        }
    }
    catch (const std::exception& e)
    {
        std::cout << "EXCEPTION: " << e.what() << "\n";
    }

    try
    {
        // One call to `Close` is required for each call to `Initialize`.
        peak::Library::Close();
    }
    catch (const std::exception& e)
    {
        std::cout << "EXCEPTION: " << e.what() << "\n";
    }
    WaitForEnterPressed();
    return EXIT_SUCCESS;
}

namespace
{

std::string TryReadString(peak::core::NodeMap& nodeMap, const std::string& nodeName)
{
    try
    {
        return nodeMap.FindNode<peak::core::nodes::StringNode>(nodeName)->Value();
    }
    catch (const std::exception&)
    {
        return "(unknown)";
    }
}

void WaitForEnterPressed()
{
    std::cout << "\nPress Enter to exit...\n";
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
    std::cin.get();
}

} // namespace
