amlt project create xujia-job conversationhub unilm
amlt project checkout xujia-job conversationhub unilm
amlt workspace add NLC_Workspace --resource-group conversationhub --subscription 90b9bfec-2ded-494a-9ccc-b584c55f454f
amlt workspace add --subscription 90b9bfec-2ded-494a-9ccc-b584c55f454f --resource-group DNN Workspace_NLC
amlt workspace add workspace_genai --resource-group cleanupservice --subscription 90b9bfec-2ded-494a-9ccc-b584c55f454f
