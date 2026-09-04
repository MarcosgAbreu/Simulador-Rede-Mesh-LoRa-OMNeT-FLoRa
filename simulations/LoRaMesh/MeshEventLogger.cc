#include "MeshEventLogger.h"

#include <stdexcept>

MeshEventLogger::MeshEventLogger(const std::string& path)
{
    stream.open(path);
    if (!stream) {
        throw std::runtime_error("não foi possível abrir o log de eventos: " + path);
    }
}

MeshEventLogger::~MeshEventLogger()
{
    close();
}

void MeshEventLogger::write(const std::string& json)
{
    stream << json << '\n';
    stream.flush();
}

void MeshEventLogger::close()
{
    if (stream.is_open())
        stream.close();
}
