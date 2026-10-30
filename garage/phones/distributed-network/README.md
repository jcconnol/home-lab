# One neural network split across two devices

Use the [phone hub](../hub/README.md), create a split-network match, and join from two differently paired browsers. Select "Compute my layer" on each assigned device, or opt in to automatic actions.

The first phone executes a 4→4 dense ReLU layer; the second executes a 4→2 linear layer on the first phone's output. The hub checks each returned tensor, stage identity, numeric tolerance, and a two-minute deadline. Completed output is compared with the unsplit Python reference. The actual multiplication runs in the browsers; this is not a server-only simulation.

The included weights are untrained test weights. This verifies distributed inference plumbing; it is not a distributed language model and does not demonstrate a performance gain. Moving a real large model onto a heterogeneous phone fleet needs phone/OS/runtime details, model conversion, memory budgeting, and further work.
