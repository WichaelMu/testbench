#pragma once

#if defined(_WIN32) || defined(_WIN64)
  #define FF_WINDOWS 1
#else
  #define FF_WINDOWS 0
#endif

#if !FF_WINDOWS
  #define FF_LINUX 1
#else
  #define FF_LINUX 0
#endif
