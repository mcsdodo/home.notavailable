# Simplify Caddy Agent Configuration                                                                                          
                                                                                                                                  
Goal                                                                                                                        
                                                                                                                        
Reduce configuration complexity from 4 env vars to 2 by removing redundant AGENT_MODE, CADDY_API_URL, and CADDY_SERVER_URL. 
                                                                                                                        
Changes to caddy-agent-watch.py                                                                                             
                                                                                                                        
1. Remove deprecated env vars:                                                                                              
- Remove AGENT_MODE (standalone/server/agent)                                                                             
- Remove CADDY_API_URL                                                                                                    
- Remove CADDY_SERVER_URL                                                                                                 
2. Add simplified env vars:                                                                                                 
- CADDY_URL - Single URL for Caddy API (default: http://localhost:2019)                                                   
- HOST_IP - If set, use for upstreams (enables "remote mode")                                                             
3. Simplify logic:                                                                                                          
CADDY_URL = os.getenv("CADDY_URL", "http://localhost:2019")                                                                 
HOST_IP = os.getenv("HOST_IP", None)                                                                                        
                                                                                                                        
# Remote mode is implied when HOST_IP is set                                                                                
is_remote_mode = HOST_IP is not None                                                                                        
4. Update all functions that reference old env vars                                                                         
                                                                                                                        
Changes to Docker Compose files                                                                                             
                                                                                                                        
docker-compose-prod-server.yml (host1):                                                                                     
environment:                                                                                                                
- CADDY_URL=http://localhost:2019                                                                                         
- AGENT_ID=host1-server                                                                                                   
# No HOST_IP = local mode (use container names)                                                                           
                                                                                                                        
docker-compose-prod-agent2.yml (host2):                                                                                     
environment:                                                                                                                
- CADDY_URL=http://192.168.0.96:2019                                                                                      
- AGENT_ID=host2-remote                                                                                                   
- HOST_IP=192.168.0.98                                                                                                    
                                                                                                                        
docker-compose-prod-agent3.yml (host3):                                                                                     
environment:                                                                                                                
- CADDY_URL=http://192.168.0.96:2019                                                                                      
- AGENT_ID=host3-remote                                                                                                   
- HOST_IP=192.168.0.99                                                                                                    
                                                                                                                        
Update documentation                                                                                                        
                                                                                                                        
- Update CLAUDE.md with new env vars                                                                                        
- Update docs/CONFIGURATION.md                                                                                              
                                                                                                                        
Testing                                                                                                                     
                                                                                                                        
- Run existing unit tests (should still pass)                                                                               
- Deploy to test hosts and verify routing works 