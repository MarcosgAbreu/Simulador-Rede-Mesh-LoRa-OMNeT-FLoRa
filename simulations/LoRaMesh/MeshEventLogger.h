#ifndef __LORA_MESH_MESHEVENTLOGGER_H
#define __LORA_MESH_MESHEVENTLOGGER_H

#include <fstream>
#include <string>

class MeshEventLogger
{
  private:
    std::ofstream stream;

  public:
    explicit MeshEventLogger(const std::string& path);
    ~MeshEventLogger();
    void write(const std::string& json);
    void close();
};

#endif
