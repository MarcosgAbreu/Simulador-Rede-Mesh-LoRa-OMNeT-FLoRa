TARGET := LoRaMesh$(EXE_SUFFIX)
OUTPUT_DIR := out
OBJECTS := $(OUTPUT_DIR)/MeshSimulation.o $(OUTPUT_DIR)/MeshEventLogger.o

CONFIGFILE := $(shell opp_configfilepath)
ifeq ("$(wildcard $(CONFIGFILE))","")
$(error OMNeT++ não encontrado; execute "source ../../scripts/env.sh")
endif
include $(CONFIGFILE)

USERIF_LIBS := $(CMDENV_LIBS)
OMNETPP_LIBS := $(OPPMAIN_LIB) $(USERIF_LIBS) $(KERNEL_LIBS) $(SYS_LIBS)
COPTS := $(CFLAGS) -std=c++17 -O2 -I$(OMNETPP_INCL_DIR)

.PHONY: all clean

all: $(OUTPUT_DIR)/$(TARGET)

$(OUTPUT_DIR)/$(TARGET): $(OBJECTS)
	@mkdir -p $(OUTPUT_DIR)
	$(CXX) $(LDFLAGS) -o $@ $^ $(OMNETPP_LIBS)

$(OUTPUT_DIR)/%.o: %.cc
	@mkdir -p $(OUTPUT_DIR)
	$(CXX) $(COPTS) -c -o $@ $<

clean:
	rm -rf $(OUTPUT_DIR)
