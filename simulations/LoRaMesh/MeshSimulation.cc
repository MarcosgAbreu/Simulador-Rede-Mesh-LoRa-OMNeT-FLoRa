#include "MeshSimulation.h"

#include "MeshEventLogger.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <queue>
#include <sstream>
#include <stdexcept>

using namespace omnetpp;

Define_Module(MeshSimulation);

namespace {
constexpr int ACTIVATE_KIND = 1000;
constexpr int MESSAGE_KIND = 2000;
constexpr int GATEWAY_INDEX = -1;
}

double MeshSimulation::distance(int first, int second) const
{
    const auto& left = nodes.at(first);
    const auto& right = nodes.at(second);
    return std::hypot(left.x - right.x, left.y - right.y);
}

double MeshSimulation::distanceToGateway(int node) const
{
    const double center = par("areaSize").doubleValue() / 2.0;
    const auto& current = nodes.at(node);
    return std::hypot(current.x - center, current.y - center);
}

std::vector<int> MeshSimulation::routeToGateway(int source) const
{
    const int count = static_cast<int>(nodes.size());
    const int gateway = count;
    std::vector<int> parent(count + 1, std::numeric_limits<int>::min());
    std::queue<int> pending;
    parent[source] = -1;
    pending.push(source);

    while (!pending.empty()) {
        const int current = pending.front();
        pending.pop();
        if (current == gateway)
            break;
        for (int candidate = 0; candidate <= count; ++candidate) {
            if (candidate == current)
                continue;
            const bool candidateIsGateway = candidate == gateway;
            if (!candidateIsGateway && !nodes[candidate].active)
                continue;
            const double linkDistance =
                candidateIsGateway ? distanceToGateway(current) : distance(current, candidate);
            if (linkDistance > par("radioRange").doubleValue() ||
                parent[candidate] != std::numeric_limits<int>::min())
                continue;
            parent[candidate] = current;
            pending.push(candidate);
        }
    }

    if (parent[gateway] == std::numeric_limits<int>::min())
        return {};
    std::vector<int> reversed;
    for (int current = gateway; current != -1; current = parent[current])
        reversed.push_back(current == gateway ? GATEWAY_INDEX : current);
    std::reverse(reversed.begin(), reversed.end());
    return reversed;
}

int MeshSimulation::spreadingFactor(double distanceMeters) const
{
    const int minimum = par("spreadingFactorMin").intValue();
    const int maximum = par("spreadingFactorMax").intValue();
    const int selected = minimum + static_cast<int>(distanceMeters / 100.0);
    return std::clamp(selected, minimum, maximum);
}

int MeshSimulation::channelFrequency()
{
    std::uniform_int_distribution<int> channel(0, par("au915UplinkChannels").intValue() - 1);
    return par("au915UplinkBase").intValue() + channel(randomEngine) * 200000;
}

std::string MeshSimulation::nodeName(int node) const
{
    return node == GATEWAY_INDEX ? "gateway" : "node[" + std::to_string(node) + "]";
}

std::string MeshSimulation::escape(const std::string& value) const
{
    std::string result;
    for (const char character : value) {
        if (character == '"' || character == '\\')
            result.push_back('\\');
        result.push_back(character);
    }
    return result;
}

void MeshSimulation::logEvent(const std::string& event, int node, int source,
                              int destination, int nextHop, int hop, int ttl,
                              int messageId, double createdAt,
                              const std::string& status,
                              const std::string& dropReason)
{
    std::ostringstream json;
    json << std::fixed << std::setprecision(6);
    json << "{\"time_s\":" << simTime().dbl()
         << ",\"event\":\"" << escape(event) << "\"";
    if (node >= 0) {
        json << ",\"node_id\":\"" << nodeName(node) << "\""
             << ",\"position_m\":{\"x\":" << nodes[node].x
             << ",\"y\":" << nodes[node].y << "}";
    }
    if (source >= 0)
        json << ",\"source_id\":\"" << nodeName(source) << "\"";
    if (destination >= GATEWAY_INDEX)
        json << ",\"destination_id\":\"" << nodeName(destination) << "\"";
    if (nextHop >= GATEWAY_INDEX)
        json << ",\"next_hop_id\":\"" << nodeName(nextHop) << "\"";
    if (hop > 0)
        json << ",\"hop\":" << hop;
    if (ttl > 0)
        json << ",\"ttl\":" << ttl;
    if (messageId > 0)
        json << ",\"message_id\":\"msg-" << std::setw(6) << std::setfill('0')
             << messageId << "\"";
    if (createdAt >= 0)
        json << ",\"created_at_s\":" << createdAt
             << ",\"latency_s\":" << simTime().dbl() - createdAt;
    json << ",\"frequency_hz\":" << channelFrequency()
         << ",\"bandwidth_hz\":" << par("bandwidth").intValue()
         << ",\"spreading_factor\":" << par("spreadingFactorMin").intValue()
         << ",\"tx_power_dbm\":" << par("txPower").doubleValue()
         << ",\"payload_bytes\":" << par("payloadBytes").intValue()
         << ",\"status\":\"" << escape(status) << "\"";
    if (!dropReason.empty())
        json << ",\"drop_reason\":\"" << escape(dropReason) << "\"";
    if (source >= 0 && nextHop >= 0) {
        const double linkDistance = distance(source, nextHop);
        json << ",\"rssi_dbm\":" << -40.0 - 20.0 * std::log10(std::max(1.0, linkDistance))
             << ",\"snr_db\":" << 10.0 - linkDistance / 100.0;
    }
    json << "}";
    logger->write(json.str());
}

void MeshSimulation::handleActivation(int node)
{
    nodes[node].active = true;
    logEvent("NODE_ACTIVATED", node);
    for (int candidate = 0; candidate < static_cast<int>(nodes.size()); ++candidate) {
        if (candidate == node || !nodes[candidate].active)
            continue;
        if (distance(node, candidate) <= par("radioRange").doubleValue()) {
            logEvent("NEIGHBOR_DISCOVERED", node, node, candidate, candidate);
        }
    }
    auto* message = new cMessage("create-message");
    message->setKind(MESSAGE_KIND + node);
    const simtime_t messageTime = simTime() + 1.0;
    if (messageTime <= simulationTime)
        scheduleAt(messageTime, message);
    else
        delete message;
}

void MeshSimulation::handleGatewayDelivery(int source, int messageId,
                                            double createdAt,
                                            const std::vector<int>& route)
{
    int current = source;
    int hop = 0;
    const int maxHops = par("maxHops").intValue();
    const int ttl = maxHops;
    for (std::size_t index = 1; index < route.size(); ++index) {
        const int next = route[index];
        ++hop;
        if (hop > maxHops) {
            logEvent("PACKET_DROPPED", current, source, GATEWAY_INDEX, next, hop,
                     ttl - hop, messageId, createdAt, "dropped", "TTL_EXPIRED");
            return;
        }
        const double linkDistance = next == GATEWAY_INDEX
                                        ? distanceToGateway(current)
                                        : distance(current, next);
        logEvent("TRANSMISSION_STARTED", current, source, GATEWAY_INDEX, next,
                 hop, ttl - hop + 1, messageId, createdAt);
        logEvent("PACKET_RECEIVED", next == GATEWAY_INDEX ? GATEWAY_INDEX : next, source,
                 GATEWAY_INDEX, next, hop, ttl - hop, messageId, createdAt);
        if (next == GATEWAY_INDEX) {
            logEvent("PACKET_DELIVERED", GATEWAY_INDEX, source, GATEWAY_INDEX,
                     GATEWAY_INDEX, hop, ttl - hop, messageId, createdAt);
            return;
        }
        logEvent("PACKET_FORWARDED", next, source, GATEWAY_INDEX, next, hop,
                 ttl - hop, messageId, createdAt);
        current = next;
        (void)linkDistance;
    }
}

void MeshSimulation::handleMessageCreation(int source)
{
    const int messageId = nextMessageId++;
    const double createdAt = simTime().dbl();
    logEvent("MESSAGE_CREATED", source, source, GATEWAY_INDEX, source,
             0, par("maxHops").intValue(), messageId, createdAt);
    const auto route = routeToGateway(source);
    if (route.empty()) {
        logEvent("PACKET_DROPPED", source, source, GATEWAY_INDEX,
                 std::numeric_limits<int>::min(), 0,
                 par("maxHops").intValue(), messageId, createdAt,
                 "dropped", "NO_ROUTE");
        return;
    }
    handleGatewayDelivery(source, messageId, createdAt, route);
}

void MeshSimulation::initialize()
{
    simulationTime = par("simulationTime").doubleValue();
    randomEngine.seed(static_cast<unsigned int>(par("seed").intValue()));
    nodes.resize(par("numNodes").intValue());
    const double area = par("areaSize").doubleValue();
    std::uniform_real_distribution<double> coordinate(0.0, area);
    std::uniform_real_distribution<double> activation(
        par("activationMin").doubleValue(), par("activationMax").doubleValue());
    for (auto& node : nodes) {
        node.x = coordinate(randomEngine);
        node.y = coordinate(randomEngine);
    }

    const std::filesystem::path output =
        par("outputDir").stdstringValue();
    std::filesystem::create_directories(output);
    logger = std::make_unique<MeshEventLogger>((output / "events.jsonl").string());
    logEvent("SIMULATION_STARTED");
    for (int node = 0; node < static_cast<int>(nodes.size()); ++node) {
        auto* message = new cMessage(("activate-node-" + std::to_string(node)).c_str());
        message->setKind(ACTIVATE_KIND + node);
        scheduleAt(activation(randomEngine), message);
    }
}

void MeshSimulation::handleMessage(cMessage* message)
{
    const std::string name = message->getName();
    if (name.rfind("activate-node-", 0) == 0) {
        handleActivation(std::stoi(name.substr(std::string("activate-node-").size())));
    }
    else if (name == "create-message") {
        handleMessageCreation(message->getKind() - MESSAGE_KIND);
    }
    delete message;
}

void MeshSimulation::finish()
{
    logEvent("SIMULATION_FINISHED");
    if (logger)
        logger->close();
}
