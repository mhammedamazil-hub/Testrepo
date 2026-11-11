// Optional self-hosted signalling only. Race state/physics never goes here.
const {PeerServer}=require('../../engine/node_modules/peer');
const server=PeerServer({host:'0.0.0.0',port:Number(process.env.PORT||9000),path:'/peerjs',proxied:true,allow_discovery:false});
server.on('connection',()=>{});console.log('Peer signalling listening on 0.0.0.0:'+(process.env.PORT||9000));
