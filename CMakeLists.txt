cmake_minimum_required(VERSION 3.13)
project(bit_encoding_approx_pattern_matching LANGUAGES CXX)

# Require C++17 as mandated by Microsoft SEAL
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Force high optimization flags for EPYC processor
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native")

find_package(SEAL REQUIRED)

add_executable(pattern_matching main.cpp)

target_link_libraries(pattern_matching SEAL::seal)
