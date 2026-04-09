cmake_minimum_required(VERSION 3.10 FATAL_ERROR)
project(point_cloud_from_file LANGUAGES C CXX)

add_executable(${PROJECT_NAME} main.cpp)

set_target_properties(${PROJECT_NAME} PROPERTIES
        CXX_STANDARD 14
        CXX_STANDARD_REQUIRED ON
        CXX_EXTENSIONS OFF
)

find_package(ids_peak_icv 1.1 REQUIRED)

# These functions will add a post-build steps to your target
# in order to copy all needed files (e.g. DLL's) to the output directory.
ids_peak_icv_deploy(${PROJECT_NAME})

target_link_libraries(${PROJECT_NAME} PRIVATE ids_peak_icv)

# add definition to a directory containing all needed files (images, configs, ...) for the sample
target_compile_definitions(${PROJECT_NAME} PRIVATE DATA_PATH="${CMAKE_CURRENT_LIST_DIR}/../../data")
