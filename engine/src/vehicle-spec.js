import model from '../roadster-model.json' with {type:'json'};

/** Research-informed game configuration, NOT manufacturer-certified telemetry.
 * Historical announced 2020 concept: AWD, 10,000 Nm wheel torque, 1.9s claimed
 * 0–60. Mass, power, tire coefficients, springs and aero below are estimates.
 * Driving-only configuration. Opt-in fictional flight lives in flight.js, not Tesla telemetry.
 */
export const ROADSTER=Object.freeze({
 name:'Roadster 2020', mass:2200, centerOfMassHeight:.55,
 wheelTorque:10000, power:800000, frontDriveShare:.4,
 suspensionRest:.24, suspensionTravel:.16, suspensionStiffness:45,
 compressionDamping:5.5, reboundDamping:7, maxSuspensionForce:16000,
 dryGrip:1.35, grassGrip:.65, brakeForce:30000, rollingCoefficient:.012,
 airDensity:1.225, dragArea:.58, downforceArea:.35, steeringMax:.5,
 reverseLimit:10, wheels:model.wheels,
 assumptions:'2200kg, 800kW, suspension/aero/tire data are explicit engineering estimates, not published Tesla measurements.'
});
