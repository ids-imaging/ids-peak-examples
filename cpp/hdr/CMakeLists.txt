cmake_minimum_required(VERSION 3.10)

project(hdr)

# Find packages
if (NOT TARGET ids_peak)
    find_package(ids_peak 1.14 REQUIRED)
endif ()
if (NOT TARGET ids_peak_icv)
    find_package(ids_peak_icv 1.4 REQUIRED)
endif ()

add_executable(${PROJECT_NAME}
        main.cpp
        camera.hpp
        camera.cpp
        hdr.hpp
        hdr.cpp
        utils.hpp
)

# Set C++ standard
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

target_compile_features(${PROJECT_NAME}
        PUBLIC
        cxx_std_${CMAKE_CXX_STANDARD}
)

# disable C++ compiler extensions e.g. GNU
set_target_properties(${PROJECT_NAME}
        PROPERTIES
        CXX_STANDARD ${CMAKE_CXX_STANDARD}
        CXX_STANDARD_REQUIRED YES
        CXX_EXTENSIONS OFF
)

target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(${PROJECT_NAME} PRIVATE
        ids_peak::ids_peak
        ids_peak_icv::ids_peak_icv
)

# Enable multiprocessing for MSVC
if (MSVC)
    target_compile_options(${PROJECT_NAME}
            PRIVATE "/MP"
    )
endif ()

# Deploy steps
ids_peak_deploy(${PROJECT_NAME})
ids_peak_icv_deploy(${PROJECT_NAME})

# For unix Build we need the environment variable GENICAM_GENTL32_PATH respectivily GENICAM_GENTL64_PATH to find the GenTL producer libraries.
# To set these environment variables a shell script is used. This script can be automatically generated via ids_peak_generate_starter_script.
# The shell script will be saved at ${CMAKE_CURRENT_BINARY_DIR}/${targetName}.sh and automatically copied to the output directory during post-build.

# To run the examples run this script, not the binary.
if (UNIX)
    ids_peak_generate_starter_script(${PROJECT_NAME})
endif ()
