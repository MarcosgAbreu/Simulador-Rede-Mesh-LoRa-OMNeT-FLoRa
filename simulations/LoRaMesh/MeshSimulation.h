#ifndef __LORA_MESH_MESHSIMULATION_H
#define __LORA_MESH_MESHSIMULATION_H

#include <omnetpp.h>

#include <memory>
#include <random>
#include <string>
#include <vector>

class MeshEventLogger;

class MeshSimulation : public omnetpp::cSimpleModule
{
  private:
    struct Node {
        double x = 0.0;
        double y = 0.0;
        bool active = false;
    };

    std::vector<Node> nodes;
    std::mt19937 randomEngine;
    std::unique_ptr<MeshEventLogger> logger;
    int nextMessageId = 1;
    omnetpp::simtime_t simulationTime;

    double distance(int first, int second) const;
    double distanceToGateway(int node) const;
    std::vector<int> routeToGateway(int source) const;
    int spreadingFactor(double distanceMeters) const;
    int channelFrequency() ;
    std::string nodeName(int node) const;
    std::string escape(const std::string& value) const;
    void logEvent(const std::string& event, int node = -2, int source = -2,
                  int destination = -2, int nextHop = -2, int hop = 0,
                  int ttl = 0, int messageId = 0, double createdAt = -1.0,
                  const std::string& status = "accepted",
                  const std::string& dropReason = "");
    void handleActivation(int node);
    void handleMessageCreation(int source);
    void handleGatewayDelivery(int source, int messageId, double createdAt,
                               const std::vector<int>& route);

  protected:
    virtual void initialize() override;
    virtual void handleMessage(omnetpp::cMessage *message) override;
    virtual void finish() override;
};

#endif
