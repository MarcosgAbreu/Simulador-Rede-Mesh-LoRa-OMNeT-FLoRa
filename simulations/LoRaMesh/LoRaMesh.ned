simple MeshSimulation
{
    parameters:
        int numNodes = default(10);
        double areaSize @unit(m) = default(1000m);
        double activationMin @unit(s) = default(0s);
        double activationMax @unit(s) = default(3600s);
        double simulationTime @unit(s) = default(14400s);
        int seed = default(1);
        double initialMessageInterval @unit(s) = default(300s);
        int maxHops = default(8);
        int maxRetries = default(2);
        int payloadBytes = default(24);
        double radioRange @unit(m) = default(450m);
        int spreadingFactorMin = default(7);
        int spreadingFactorMax = default(12);
        int bandwidth = default(125000);
        double txPower = default(14);
        int au915UplinkBase = default(915200000);
        int au915UplinkChannels = default(64);
        string outputDir = default("runs");
        @display("i=device/pc");
}

network LoRaMesh
{
    parameters:
        @display("bgb=1000,700");
    submodules:
        simulation: MeshSimulation {
            parameters:
                numNodes = default(10);
                @display("p=500,350");
        }
}
