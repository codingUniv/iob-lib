
VSRC+=iob_diff.v
iob_diff.v:$(LIB_DIR)/hardware/iob_diff/iob_diff.v
	cp $< $(BUILD_VSRC_DIR)
