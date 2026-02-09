cmake_minimum_required(VERSION 3.10 FATAL_ERROR)
project(system_timestamp LANGUAGES C CXX)

add_executable(${PROJECT_NAME} main.cpp)

set_target_properties(${PROJECT_NAME} PROPERTIES
    CXX_STANDARD 14
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)

find_package(ids_peak REQUIRED)

# These functions will add a post-build steps to your target
# in order to copy all needed files (e.g. DLL's) to the output directory.
ids_peak_deploy(${PROJECT_NAME})

target_link_libraries(${PROJECT_NAME} PRIVATE ids_peak)
